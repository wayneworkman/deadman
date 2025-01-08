# Secure Power-Cut Add-On — Requirements Document

## 1. Purpose and Scope

1. **Primary Goal**  
   - Build an external hardware device that controls AC power (up to 240 VAC / 15 A) to a protected Linux system, ensuring **guaranteed power loss** when specific security conditions fail (heartbeat failure, tampering, or user-initiated emergency off).

2. **Fail-Safe Principle**  
   - No battery backup: if this device loses power, the protected system also loses power.  
   - If attackers try to remove or bypass the device, the system inevitably loses power.

3. **Two-Way Heartbeat & Disarm**  
   - The protected system runs `deadman.py`, which exchanges encrypted challenge-response messages with this device every second.  
   - If these messages fail for **5 seconds**, the device cuts power, and `deadman.py` also attempts a software shutdown.  
   - Authorized users can **disarm** the device (via `deadman.service stop`), at which point sensor triggers are ignored until re-armed. The disarm command is itself **encrypted**, ensuring no unauthorized disarm is possible.

---

## 2. Hardware Overview

1. **Relay (SSR or Mechanical)**  
   - Must handle 240 VAC, 15 A.  
   - Should provide **fast, reliable** switching. SSRs switch faster but can leak current and generate heat; mechanical relays offer full galvanic isolation but have limited switching cycles.

2. **Controller Board**  
   - **Candidate 1**: Microcontroller (e.g., Adafruit rp2350 with an RP2350 chip) running CircuitPython/MicroPython plus a secure-boot capable firmware.  
   - **Candidate 2**: Raspberry Pi Zero v1.3 (no Wi-Fi), using a minimal Linux environment, standard crypto libraries, and an SD card (less ideal for tamper, but simpler for USB connectivity).  

3. **Watchdog Mechanism**  
   - A **hardware watchdog** is required to ensure the microcontroller or Pi Zero code cannot hang indefinitely.  
   - If the controller’s main loop stalls or the firmware crashes, the watchdog times out, prompting a hard reset or a forced power cut to the protected system.

4. **Enclosure**  
   - Metal, locked case with multiple tamper sensors to detect opening.  
   - The device includes a **big red emergency off button** externally, which physically breaks the circuit when pressed.

---

## 3. Security & Tamper Detection

1. **Multiple Sensors**  
   - **Photodiodes**: More than one photodiode to detect enclosure opening (light intrusion).  
   - **IMU(s)**: At least two BNO085 IMUs for redundancy, detecting any unexpected motion/acceleration/orientation changes.  
   - **Switches**: Multiple mechanical switches on case doors/panels.  
   - **AC Bypass Detection**: If the relay is open but the output side still has voltage/current (indicating possible bypass), the device cuts power immediately.

2. **Tamper Consequences**  
   - If the device is **armed** (i.e., not in disarmed mode) and any tamper sensor triggers, the device cuts power **instantly**.  
   - In parallel, it sends a message to `deadman.py` (if still powered by USB) to initiate software shutdown. But practically, the AC power is killed at once.

3. **Disarm Mode**  
   - When a privileged user on the Linux system stops the `deadman.service`, an **encrypted “disarm”** command is sent to the device.  
   - While disarmed, **no sensor triggers** cause a power cut. This permits authorized maintenance, such as opening the case.  
   - The system re-arms (and thus re-enables tamper triggers) when `deadman.service` is started again, performing a new ephemeral key exchange.

---

## 4. Operational States and Timers

1. **Power-Up and Grace Period**  
   - The device enforces a **60-second grace period** after powering on, **only if** the protected system was **off** for at least 5 seconds prior.  
   - During this grace period, **no** sensor events or missed heartbeats trigger power cuts. This allows normal setup (positioning, final cable checks, etc.).  
   - A capacitor (monitored via an ADC) may measure whether the system has indeed stayed off for 5+ seconds before re-powering. If not, the device remains latched off or repeats a partial sequence.

2. **Heartbeat**  
   - After the 60-second grace period (if triggered) and successful ephemeral key exchange, the device and `deadman.py` exchange an encrypted challenge-response **every 1 second**.  
   - If 1 second passes with no valid message, the device initiates a **5-second countdown**.  
   - If no valid heartbeat arrives before those 5 seconds are up, the device cuts power, and `deadman.py` also issues a software shutdown if possible.

3. **First 60 Seconds Connectivity**  
   - If the device cannot connect to `deadman.py` at all within the initial 60-second grace, it remains powered. The system is presumably already secure because the data volumes are encrypted at rest.  
   - After that, the device arms itself. If no valid heartbeats occur thereafter, the standard 5-second countdown to power cut applies.

4. **Watchdog Behavior**  
   - A hardware watchdog ensures the controller code cannot freeze. If it does, the watchdog triggers an internal reset or directs a **power cut** to the system.  
   - The device firmware must periodically “pet” (feed) this watchdog to confirm it’s running valid code.

5. **Automatic Re-Power**  
   - After cutting power, the device can automatically restore AC after ~5 seconds. The system reboots into an encrypted state, requiring user authentication (password/token).  
   - If the user wants the system to stay off, they can physically disconnect cables, or the device can remain latched off if designed so.

---

## 5. Communication & Cryptography

1. **Ephemeral Keys**  
   - No permanent key is stored on either side.  
   - On each boot/power cycle, `deadman.py` and the device perform a secure ephemeral key exchange (e.g., Diffie-Hellman or ECDH).  
   - Both sides store the derived key **only in RAM**, ensuring no attacker can trivially extract it from flash or firmware.

2. **Encrypted Challenge-Response**  
   - The device and `deadman.py` exchange encrypted messages. Each message must be validated with a fresh nonce to prevent replay.  
   - If the device receives an **invalid** or **missing** message, it checks if the 5-second grace for heartbeats is exceeded, then kills power.  
   - If `deadman.py` sees invalid or missing responses from the device, it initiates a software shutdown.

3. **Disarm Command**  
   - The “disarm” message (when `deadman.service` is stopped by an authorized root user) is also encrypted and signed, so no rogue process can trivially disarm the device.

4. **Library Choices**  
   - On the RP2350 board, you can use CircuitPython or mbedTLS.  
   - On a Pi Zero, you can rely on standard Linux cryptographic libraries (OpenSSL, etc.).  
   - Regular library updates are recommended, though you acknowledge it may not happen frequently.

---

## 6. Physical Safety and Deployment

1. **Enclosure Requirements**  
   - Metal, tamper-resistant enclosure housing the relay, sensors, and controller.  
   - Multiple photodiodes, multiple mechanical switches, and at least two IMUs for motion detection.  
   - All tamper sensors connect to the microcontroller or Pi in a secure manner (no easy external wiring to bypass).

2. **Wiring & Cabling**  
   - The device sits between the AC supply and the system’s power inlet.  
   - Possibly pot or seal the cables to prevent easy bypass. If an attacker unplugs the device from the load side, the system is effectively off anyway.

3. **Emergency Off Button**  
   - A large external button that forcibly breaks the AC circuit. This is a user-friendly way to cut power on demand (in addition to sensor or software triggers).

4. **Redundancy & Reliability**  
   - The design should minimize single points of failure. Multiple sensors for tamper detection, hardware watchdog for firmware operation, and robust relay for power switching.  
   - An internal fuse or breaker might be included for additional electrical safety, and heat dissipation must be managed (especially for SSR under load).

---

## 7. Usage Flow Summary

1. **System Off → Power On**  
   - If system was off ≥5 seconds, the device grants a 60-second grace period with no sensor triggers. Meanwhile, it attempts to establish encryption with `deadman.py`.

2. **Arming & Steady Operation**  
   - After 60 seconds (or if power was cycled quickly), the device arms itself:  
     - Challenge-response heartbeats begin every 1 second.  
     - Sensors are active, except if the device is disarmed by a secure command from the system.  
     - Any tamper (movement, enclosure opening, AC bypass) → immediate power cut.  
     - Missed or invalid heartbeats for 5 seconds → power cut.

3. **Disarming**  
   - If the user stops `deadman.service` with appropriate privileges, an encrypted “disarm” is sent to the device.  
   - While disarmed, sensor triggers do **not** cut power (including motion or enclosure opening).  
   - The user can perform maintenance safely. Re-arming occurs when the user restarts the service, forcing a new ephemeral key exchange.

4. **Cutting Power & Recovery**  
   - If triggered, the relay opens, instantly removing AC from the system.  
   - After ~5 seconds, the device can close the relay again automatically, allowing a reboot into an encrypted state.  
   - The user can physically disconnect cables if they want to keep the system off indefinitely.

---

## 8. Final Statement of Requirements

- **All** tamper events or missed heartbeats lead to **immediate** or near-immediate power cut, **unless** the device is explicitly **disarmed**.  
- **Multiple redundant sensors** (photodiodes, IMUs, switches) detect any suspicious change.  
- The **watchdog** ensures the controller firmware is always running; if it hangs, the hardware resets or cuts power.  
- A 60-second startup grace period applies only if the system was off for at least 5 seconds, letting the device calibrate sensors before going armed.  
- **Full ephemeral encryption** for heartbeats and disarm commands prevents forging or replay attacks.  
- A **big red emergency button** is included for user-initiated power cuts at any time.

