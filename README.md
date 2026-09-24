# Safe Cracker
 
A full-stack app that cracks a 10-digit safe combination using only a "spy tool" that reports **how many digits of a guess are in the correct position**. It has a Flask backend and a lightweight HTML/JavaScript frontend that shows the cracking progress live, digit by digit.
 
Built for the forml coding assessment (Part 2).
 
---
 
## Features
 
- **Efficient cracking algorithm:** solves any 10-digit combination in at most 81 guesses (about 46 on average) instead of up to 10,000,000,000 by brute force
- **Live progress view:** each guess, its score, and the combination filling in as it's solved, streamed from the server in real time
- **Safe animation:** the safe image opens when the combination is cracked and closes when a new attempt starts
- **Random combination button:** fills in a random 10-digit code for quick testing
- **Adjustable delay:** optional per-guess delay (0–500 ms) so progress is visible to the eye
- **Input validation:** the server rejects anything that isn't exactly 10 digits
---
 
## Getting started
 
### Requirements
 
- Python 3.10+
- Flask (listed in `requirements.txt`)
### Run it
 
```bash
# 1. Create and activate a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
 
# 2. Install dependencies
pip install -r requirements.txt
 
# 3. Start the server
python main.py
```
 
Then open **http://127.0.0.1:5000** in your browser.
 
> On Windows, if `python` or `pip` point to different installations, use `py -m pip install -r requirements.txt` and `py main.py` so both use the same interpreter.
 
---
 
## How the algorithm works
 
The only feedback available is the **number of correct positions** in a guess. The spy tool never says *which* positions are correct.
 
**Key idea:** if you change **only one position** relative to a fixed baseline, any change in the score must come from that position.
 
1. Guess the baseline `0000000000` and record its score.
2. For each position `i` from 0 to 9, replace position `i` with digits 1, 2, 3, … and compare each new score with the baseline:
| Score vs. baseline | Meaning |
|---|---|
| **Higher** | The new digit is correct at position `i` |
| **Lower** | The original `0` was correct at position `i` |
| **Same** | Neither digit is correct here, so try the next one |
 
3. If digits 1–8 all leave the score unchanged, the digit must be **9**. It's inferred without spending a guess.
 
---
 
## API
 
### `POST /api/crack_safe`
 
Cracks the combination in one call and returns the result.
 
**Request**
```json
{ "actual_combination": "7391473829" }
```
 
**Response**
```json
{ "combination": "7391473829", "attempts": 52, "time_ms": 0.045 }
```
 
**Error (400)**
```json
{ "error": "combination must be exactly 10 digits" }
```
 
### `GET /api/crack_safe/stream?actual_combination=…&delay_ms=…`
 
Streams progress as **Server-Sent Events**, one event per guess.
 
| Parameter | Description |
|---|---|
| `actual_combination` | The 10-digit combination to crack |
| `delay_ms` | Optional delay between guesses, 0–500 ms (default 0) |
 
**Event types**
```json
{ "type": "progress", "position": 3, "guess": "0001000000", "score": 2,
  "solved": "739???????", "attempts": 21, "time_ms": 1.2 }
 
{ "type": "done", "combination": "7391473829", "attempts": 52, "time_ms": 2.8 }
 
{ "type": "error", "error": "combination must be exactly 10 digits" }
```
 
---
 
## Project structure
 
```
safe-cracker/
├── main.py              # Flask app: cracking logic, API routes, and frontend page
├── media/
│   ├── safe_closed.jpg  # Shown while locked / cracking
│   └── safe_open.jpg    # Shown once cracked
├── requirements.txt
└── README.md
```
 
### Inside `main.py`
 
| Component | Purpose |
|---|---|
| `SafeUtils` | Wraps the spy tool and tracks the attempt count and elapsed time |
| `crack_safe_actual()` | Runs the algorithm to completion and returns the combination, attempts, and time |
| `crack_safe_steps()` | The same algorithm written as a **generator**: it `yield`s a status update after every guess |
| `/api/crack_safe` | JSON endpoint for a single result |
| `/api/crack_safe/stream` | SSE endpoint for live progress |
| `PAGE` | The HTML/JavaScript frontend |
