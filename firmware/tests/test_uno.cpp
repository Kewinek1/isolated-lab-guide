#include <assert.h>
#include <string.h>
#include "../uno_serial/commands.h"

int main() {
  CommandBuffer b;
  const char* on = "LED ON\r\n";
  int ready = 0;
  for (unsigned int i = 0; i < strlen(on); ++i) {
    if (b.feed(on[i]) == CommandBuffer::READY) {
      ++ready;
      assert(parseCommand(b.text) == LED_ON);
    }
  }
  assert(ready == 1);  // CRLF produces exactly one command.
  for (int i = 0; i < 80; ++i) assert(b.feed('A') == CommandBuffer::WAITING);
  assert(b.feed('\n') == CommandBuffer::REJECTED);
  const char* status = "STATUS\n";
  for (unsigned int i = 0; i < strlen(status); ++i) b.feed(status[i]);
  assert(parseCommand(b.text) == STATUS);  // Recovers after a discarded line.
  b.feed('L'); b.feed('\0'); b.feed('D');
  assert(b.feed('\n') == CommandBuffer::REJECTED);
  assert(parseCommand("LED ON; STATUS") == UNKNOWN);
  assert(parseCommand("led on") == UNKNOWN);
  assert(parseCommand("LED OFF") == LED_OFF);
  assert(parseCommand("PING") == PING);
  assert(parseCommand("HELP") == HELP);
  return 0;
}
