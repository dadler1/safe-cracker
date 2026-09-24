from flask import Flask, Response, jsonify, request, render_template_string
import json
import time

app = Flask(__name__, static_folder="media", static_url_path="/media")


class SafeUtils:
    def __init__(self):
        self.attempts = 0
        self.start_time = time.perf_counter()

    def spy_tool(self, guess, actual):
        counter = 0
        for i in range(len(guess)):
            if guess[i] == actual[i]:
                counter += 1
        self.attempts += 1
        return counter

    def get_time(self):
        return (time.perf_counter() - self.start_time) * 1000  # milliseconds

    def get_attempts(self):
        return self.attempts


def crack_safe_actual(safe_utils, actual_combination):
    base = "0" * 10
    base_score = safe_utils.spy_tool(base, actual_combination)
    answer = list(base)

    for i in range(10):
        for d in "123456789":
            score = safe_utils.spy_tool(base[:i] + d + base[i + 1:], actual_combination)
            if score > base_score:
                answer[i] = d
                break
            if score < base_score:
                break
            if d == "8":
                answer[i] = "9"
                break
    return "".join(answer), safe_utils.get_attempts(), safe_utils.get_time()


@app.post("/api/crack_safe")
def crack_safe():
    data = request.get_json(silent=True) or {}
    actual_combination = str(data.get("actual_combination", ""))
    if not actual_combination.isdigit() or len(actual_combination) != 10:
        return jsonify(error="combination must be exactly 10 digits"), 400
    safe_utils = SafeUtils()
    guess, attempts, ex_time = crack_safe_actual(safe_utils, actual_combination)
    return jsonify(
        combination=guess,
        attempts=attempts,
        time_ms=round(ex_time, 3),
    )


def crack_safe_steps(safe_utils, actual_combination, delay=0.0):
    """Same algorithm as crack_safe_actual, but yields a status update after every guess."""
    base = "0" * 10
    base_score = safe_utils.spy_tool(base, actual_combination)
    answer = list(base)
    solved = ["?"] * 10                      # what we've confirmed so far

    yield {"type": "progress", "position": None, "guess": base, "score": base_score,
           "solved": "".join(solved), "attempts": safe_utils.get_attempts(),
           "time_ms": round(safe_utils.get_time(), 3)}

    for i in range(10):
        for d in "123456789":
            guess = base[:i] + d + base[i + 1:]
            score = safe_utils.spy_tool(guess, actual_combination)
            if score > base_score:
                answer[i] = d
            elif score < base_score:
                answer[i] = "0"
            elif d == "8":
                answer[i] = "9"

            done_here = score != base_score or d == "8"
            if done_here:
                solved[i] = answer[i]

            yield {"type": "progress", "position": i, "guess": guess, "score": score,
                   "solved": "".join(solved), "attempts": safe_utils.get_attempts(),
                   "time_ms": round(safe_utils.get_time(), 3)}
            if delay:
                time.sleep(delay)
            if done_here:
                break

    yield {"type": "done", "combination": "".join(answer),
           "attempts": safe_utils.get_attempts(), "time_ms": round(safe_utils.get_time(), 3)}


@app.get("/api/crack_safe/stream")
def crack_safe_stream():
    actual_combination = request.args.get("actual_combination", "")
    delay_ms = min(max(int(request.args.get("delay_ms", 0) or 0), 0), 500)

    def sse(data):
        return f"data: {json.dumps(data)}\n\n"

    if not actual_combination.isdigit() or len(actual_combination) != 10:
        return Response(sse({"type": "error", "error": "combination must be exactly 10 digits"}),
                        mimetype="text/event-stream")

    def generate():
        safe_utils = SafeUtils()
        for update in crack_safe_steps(safe_utils, actual_combination, delay_ms / 1000):
            yield sse(update)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


PAGE = """
<!doctype html>
<title>Safe Cracker</title>
<h1>Safe Cracker</h1>
<img id="safe" src="/media/safe_closed.jpg" alt="Safe" width="250">
<br>
<input id="secret" placeholder="Secret, e.g. 7391473829" maxlength="10">
<button type="button" onclick="randomize()">Random</button>
<label>Delay per guess (ms): <input id="delay" type="number" value="50" min="0" max="500"></label>
<button id="go" onclick="crack()">Crack it</button>

<p>Status: <b id="status">idle</b></p>
<p>Solved so far: <code id="solved">??????????</code></p>
<p>Last guess: <code id="guess">-</code> &rarr; <span id="score">-</span> correct</p>
<p>Attempts: <span id="attempts">0</span> &middot; Time: <span id="time">0</span> ms</p>
<pre id="out"></pre>

<script>
let source = null;

function crack() {
  if (source) source.close();
  const params = new URLSearchParams({
    actual_combination: document.getElementById("secret").value,
    delay_ms: document.getElementById("delay").value,
  });

  setSafe(false);
  setText("status", "cracking…");
  setText("solved", "??????????");
  setText("out", "");
  document.getElementById("go").disabled = true;

  source = new EventSource(`/api/crack_safe/stream?${params}`);

  source.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "progress") {
      setText("solved", data.solved);
      setText("guess", data.guess);
      setText("score", data.score);
      setText("attempts", data.attempts);
      setText("time", data.time_ms);
    } else if (data.type === "done") {
      setText("status", "done");
      setText("solved", data.combination);
      setText("attempts", data.attempts);
      setText("time", data.time_ms);
      setText("out", `Cracked: ${data.combination} in ${data.attempts} attempts`);
      setSafe(true);
      finish();
    } else if (data.type === "error") {
      setText("status", "error");
      setText("out", `Error: ${data.error}`);
      finish();
    }
  };

  source.onerror = () => { setText("status", "connection lost"); finish(); };
}

function finish() {
  source.close();
  document.getElementById("go").disabled = false;
}

function setSafe(isOpen) {
  document.getElementById("safe").src = isOpen
    ? "/media/safe_open.jpg"
    : "/media/safe_closed.jpg";
}

function randomize() {
  let code = "";
  for (let i = 0; i < 10; i++) {
    code += Math.floor(Math.random() * 10);
  }
  document.getElementById("secret").value = code;
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}
</script>
"""


@app.get("/")
def index():
    return render_template_string(PAGE)


if __name__ == "__main__":
    app.run(debug=True, threaded=True)