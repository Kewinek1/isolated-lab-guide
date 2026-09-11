// Classic Arduino Uno / Uno R3 (ATmega328P). USB + built-in LED only.
#include "commands.h"

CommandBuffer input;
bool ledOn = false;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  Serial.begin(115200);
  Serial.println(F("LAB SERIAL READY; send HELP; newline; 115200 baud"));
}

void execute(const char* line) {
  switch (parseCommand(line)) {
    case HELP:
      Serial.println(F("HELP | STATUS | PING | LED ON | LED OFF"));
      break;
    case STATUS:
      Serial.print(F("LED="));
      Serial.print(ledOn ? F("ON") : F("OFF"));
      Serial.print(F(" UPTIME_MS="));
      Serial.println(millis());
      break;
    case PING:
      Serial.println(F("PONG"));
      break;
    case LED_ON:
    case LED_OFF:
      ledOn = parseCommand(line) == LED_ON;
      digitalWrite(LED_BUILTIN, ledOn ? HIGH : LOW);
      Serial.println(ledOn ? F("OK LED ON") : F("OK LED OFF"));
      break;
    default:
      Serial.println(F("ERROR unknown command; send HELP"));
  }
}

void loop() {
  while (Serial.available() > 0) {
    const CommandBuffer::Result result = input.feed((char)Serial.read());
    if (result == CommandBuffer::READY) execute(input.text);
    if (result == CommandBuffer::REJECTED)
      Serial.println(F("ERROR line rejected; ASCII only; maximum 63 characters"));
  }
}
