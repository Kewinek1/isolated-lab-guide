import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile, writeFile, mkdtemp, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';

// Load the browser's dependency-free ES module without requiring a package.json.
const source = await readFile(new URL('../app/model.js', import.meta.url), 'utf8');
const model = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const {sample, ipv4, network, validate, esc, scenarios, rows, command, steps, diagram} = model;

test('each site has independent valid fictional networks and target roles', () => {
  const plans = ['A', 'B', 'C'].map(sample);
  for (const [index, plan] of plans.entries()) {
    assert.deepEqual(validate(plan), []);
    assert.equal(plan.labCidr, `10.77.${(index + 1) * 10}.0/24`);
    assert.equal(plan.target, `10.77.${(index + 1) * 10}.20`);
    assert.equal(plan.pico, `10.77.${(index + 1) * 10}.30`);
    assert.equal(plan.homeCidr, '');
    assert.match(plan.relayHost, /\.example\.invalid$/);
  }
  assert.equal(new Set(plans.flatMap(p => [p.labCidr, p.relayCidr, p.managementCidr, p.serviceCidr])).size, 12);
  plans[0].mainRouter = 'Private temporary label';
  assert.equal(sample('A').mainRouter, 'Home router');
});

test('IPv4 and /24 parsing rejects ambiguous, malformed and non-network values', () => {
  assert.deepEqual(ipv4('10.77.10.20'), [10, 77, 10, 20]);
  assert.deepEqual(network('10.77.10.0/24'), [10, 77, 10, 0]);
  for (const invalid of ['10.77.10.256', '010.77.10.20', '10.77.10', '10.77.10.20 ', '10.77.10.20;id', '::1']) {
    assert.equal(ipv4(invalid), null, invalid);
  }
  for (const invalid of ['10.77.10.1/24', '10.77.10.0/16', '10.77.10.0/24/32', '10.77.10.0', '10.77.10.0/024']) {
    assert.equal(network(invalid), null, invalid);
  }
});

test('overlapping segments and invalid host assignments block plan acceptance', () => {
  for (const field of ['relayCidr', 'managementCidr', 'serviceCidr', 'homeCidr']) {
    const plan = sample('A');
    plan[field] = plan.labCidr;
    assert.ok(validate(plan).some(error => /distinct subnets/.test(error)), field);
  }
  for (const address of ['10.77.20.20', '10.77.10.0', '10.77.10.1', '10.77.10.255']) {
    assert.ok(validate({...sample('A'), target: address}).some(error => error.startsWith('target:')), address);
  }
  const plan = sample('A');
  plan.target = plan.pico;
  assert.ok(validate(plan).some(error => /different addresses/.test(error)));
});

test('untrusted labels and connection destinations cannot inject markup or shell syntax through an accepted plan', () => {
  for (const field of ['mainRouter', 'labRouter', 'firewall']) {
    for (const input of ['<script>alert(1)</script>', 'line\nfeed', 'x'.repeat(49), '']) {
      assert.ok(validate({...sample('A'), [field]: input}).some(error => error.startsWith(field + ':')));
    }
  }
  for (const field of ['relayHost', 'gameHost']) {
    for (const input of ['relay;id', '$(id)', '`id`', '-oProxyCommand=id', 'relay name', 'relay..invalid', 'relay\nother', 'user@relay']) {
      assert.ok(validate({...sample('A'), [field]: input}).some(error => error.startsWith(field + ':')), input);
    }
  }
  assert.equal(esc('&<>"\''), '&amp;&lt;&gt;&quot;&#39;');
  const rendered = diagram('offline', {...sample('A'), mainRouter: '<svg/onload=1>'});
  assert.ok(!rendered.includes('<svg/onload=1>'));
  assert.ok(rendered.includes('&lt;svg/onload=1&gt;'));
});

test('all five scenarios produce complete diagrams, five teaching steps and coherent address tables', () => {
  assert.deepEqual(scenarios.map(s => s.id), ['offline', 'single', 'tunnel', 'games', 'dmz']);
  for (const site of ['A', 'B', 'C']) {
    const plan = sample(site);
    for (const scenario of scenarios) {
      const table = rows(scenario.id, plan);
      assert.ok(table.length >= 3, `${site}/${scenario.id}`);
      assert.ok(table.every(row => row.length === 2 && row.every(value => typeof value === 'string')));
      const flow = steps(scenario.id, plan);
      assert.equal(flow.length, 5);
      assert.ok(flow.every(step => step.length === 3 && step.every(Boolean)));
      const svgBody = diagram(scenario.id, plan, flow[0][2]);
      assert.ok(svgBody.includes('diagram-title'));
      assert.ok(svgBody.includes('diagram-desc'));
      assert.ok(!svgBody.includes('undefined'));
      assert.ok(!svgBody.includes('<script'));
      assert.ok(command(scenario.id, plan).length > 40);
      if (['offline', 'single', 'tunnel'].includes(scenario.id)) {
        assert.equal(table.find(([name]) => name === 'Linux target')[1], `${plan.target}:8081`);
        assert.equal(table.find(([name]) => name === 'Pico W')[1], `${plan.pico}:8080`);
      }
    }
  }
});

test('commands preserve scoped relay bindings and distinguish game protocols', () => {
  const plan = sample('A');
  assert.ok(command('offline', plan).includes(`http://${plan.pico}:8080/status`));
  const relay = command('tunnel', plan);
  assert.ok(relay.includes(`-L 127.0.0.1:18080:${plan.pico}:8080`));
  assert.ok(relay.includes('-i ~/.ssh/lab_forwarding'));
  assert.ok(relay.includes('lab-operator-a@' + plan.relayHost));
  assert.ok(!relay.includes('0.0.0.0:'));
  const gameRows = Object.fromEntries(rows('games', plan));
  assert.equal(gameRows['Minecraft Java'], 'TCP 25565');
  assert.equal(gameRows.Factorio, 'UDP 34197');
  assert.ok(command('games', plan).includes(plan.gameHost + ':25565'));
  assert.ok(command('games', plan).includes(plan.gameHost + ':34197'));
  assert.ok(!/^\s*(ssh|curl|sudo|uci|nft)\b/m.test(command('dmz', plan)));
});

test('public SVG export rebuilds fictional examples and excludes operational plan values', () => {
  assert.equal(typeof model.publicFigure, 'function', 'Public export must use a testable model entry point');
  const privatePlan = {...sample('B'), mainRouter: 'PRIVATE_ROUTER_MARKER', labRouter: 'PRIVATE_LAB_MARKER',
    firewall: 'PRIVATE_FIREWALL_MARKER', pico: '192.168.222.30', target: '192.168.222.20',
    labCidr: '192.168.222.0/24', relayHost: 'private-relay.invalid', gameHost: 'private-games.invalid'};
  for (const scenario of scenarios) {
    // The public export accepts the site selector, not any current plan object.
    const exported = model.publicFigure(scenario.id, privatePlan.site, privatePlan);
    assert.match(exported, /^<svg\s/);
    assert.ok(exported.includes('PUBLIC EXAMPLE'));
    for (const value of ['PRIVATE_ROUTER_MARKER', 'PRIVATE_LAB_MARKER', 'PRIVATE_FIREWALL_MARKER',
      '192.168.222.', 'private-relay.invalid', 'private-games.invalid']) {
      assert.ok(!exported.includes(value), `${scenario.id} leaked ${value}`);
    }
    assert.equal(exported, model.publicFigure(scenario.id, 'B'));
  }
});

test('builder inputs match the exact public schema and never inherit enablement or credentials', async () => {
  const schema = JSON.parse(await readFile(new URL('../tools/private-config.example.json', import.meta.url), 'utf8'));
  assert.deepEqual(model.buildInputs(sample('A')), schema);
  const plan = {...sample('C'), target: '10.77.30.42', pico: '10.77.30.43', homeCidr: '192.168.222.0/24',
    addresses_confirmed: true, isolated_lab_confirmed: true, relay_internet_https: true,
    ssid: 'PRIVATE_SSID_MARKER', wifi_password: 'PRIVATE_PASSWORD_MARKER'};
  const inputs = model.buildInputs(plan);
  assert.deepEqual(Object.keys(inputs).sort(), Object.keys(schema).sort());
  assert.equal(inputs.target_ip, '10.77.30.42');
  assert.equal(inputs.pico_ip, '10.77.30.43');
  assert.deepEqual(inputs.protected_home_cidrs, ['192.168.222.0/24']);
  assert.deepEqual(inputs.protected_external_cidrs, []);
  assert.equal(inputs.addresses_confirmed, false);
  assert.equal(inputs.isolated_lab_confirmed, false);
  assert.equal(inputs.relay_internet_https, false);
  assert.deepEqual(inputs.pico, {enable_network: false, ssid: null, wifi_password: null, country: 'XX'});
  assert.ok(!JSON.stringify(inputs).includes('PRIVATE_'));
  for (const invalid of [{...plan, target: '10.77.10.42'}, {...plan, pico: plan.target},
    {...plan, relayHost: 'host;id'}, {...plan, relayCidr: plan.labCidr}, {...plan, site: 'unknown'},
    {...plan, relayCidr: '203.0.113.0/24'}]) {
    assert.throws(() => model.buildInputs(invalid));
  }
});

test('edited plan JSON is consumed by the real private builder with custom addresses preserved', async () => {
  const privateDirectory = await mkdtemp(join(tmpdir(), 'plan-builder-test-'));
  try {
    const plan = {...sample('B'), target: '10.77.20.52', pico: '10.77.20.53'};
    await writeFile(join(privateDirectory, 'config.local.json'), JSON.stringify(model.buildInputs(plan)), {mode: 0o600});
    const builder = fileURLToPath(new URL('../tools/materialize.py', import.meta.url));
    const result = spawnSync('python3', [builder, '--private-dir', privateDirectory], {
      encoding: 'utf8', env: {...process.env, PYTHONDONTWRITEBYTECODE: '1'}, timeout: 10000,
    });
    assert.equal(result.status, 0, result.stderr);
    const site = JSON.parse(await readFile(join(privateDirectory, 'build/network/site.local.json'), 'utf8'));
    assert.deepEqual(site.target_services, [{address: plan.pico, tcp_port: 8080}, {address: plan.target, tcp_port: 8081}]);
    const ssh = await readFile(join(privateDirectory, 'build/network/sshd-relay.conf.example'), 'utf8');
    assert.ok(ssh.includes(`PermitOpen ${plan.pico}:8080 ${plan.target}:8081`));
    assert.ok(!ssh.includes('10.77.10.30:8080'));
    const pico = await readFile(join(privateDirectory, 'build/firmware/pico_w/config.py'), 'utf8');
    assert.ok(pico.includes('ENABLE_NETWORK = False'));
    await assert.rejects(readFile(join(privateDirectory, 'build/network/firewall.candidate')));
  } finally {
    await rm(privateDirectory, {recursive: true, force: true});
  }
});
