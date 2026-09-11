#ifndef HOMELAB_COMMANDS_H
#define HOMELAB_COMMANDS_H

#include <stdint.h>
#include <string.h>

// One command per line. No heap allocation and no partial execution after overflow.
class CommandBuffer {
 public:
  enum Result { WAITING, READY, REJECTED };
  static const uint8_t CAPACITY = 64;
  char text[CAPACITY];

  CommandBuffer() : length_(0), discard_(false), after_cr_(false) { text[0] = '\0'; }

  Result feed(char c) {
    if (c == '\n' && after_cr_) { after_cr_ = false; return WAITING; }
    after_cr_ = false;
    if (c == '\r' || c == '\n') {
      after_cr_ = (c == '\r');
      text[length_] = '\0';
      const bool rejected = discard_;
      const bool empty = length_ == 0;
      length_ = 0;
      discard_ = false;
      return rejected ? REJECTED : (empty ? WAITING : READY);
    }
    if (discard_) return WAITING;
    if (c < 32 || c > 126 || length_ >= CAPACITY - 1) {
      discard_ = true;
      return WAITING;
    }
    text[length_++] = c;
    return WAITING;
  }

 private:
  uint8_t length_;
  bool discard_;
  bool after_cr_;
};

enum Command { UNKNOWN, HELP, STATUS, PING, LED_ON, LED_OFF };

inline Command parseCommand(const char* line) {
  if (strcmp(line, "HELP") == 0) return HELP;
  if (strcmp(line, "STATUS") == 0) return STATUS;
  if (strcmp(line, "PING") == 0) return PING;
  if (strcmp(line, "LED ON") == 0) return LED_ON;
  if (strcmp(line, "LED OFF") == 0) return LED_OFF;
  return UNKNOWN;
}

#endif
