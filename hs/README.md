# High School Learning Version

This folder contains educational versions of the LED Matrix Camera Feed code, designed for high school students learning Python programming.

> 💡 New here? Read [**Why Learn to Code if AI Can Write It?**](../docs/why-learn-to-code.md) —
> how this project was built with AI, and why you still need to learn programming.

## What's Different?

Compared to the `pro/` version, this version has:

- **Extensive comments** explaining every section of code
- **Simplified logic** using multiplication/division instead of bit shifting
- **Debug output** showing what's happening at each step
- **Visual preview** windows to see the camera and matrix output
- **Glossary terms** defining technical vocabulary
- **Interactive keyboard controls** for display modes and effects
- **Snapshot feature** with countdown overlay
- **Avatar capture mode** with guided voice prompts
- **Beginner-friendly error messages** with troubleshooting tips

## Files

### src/
Unified version for both macOS and Raspberry Pi:
- `config.py` - Settings with explanations
- `camera_feed.py` - Main program with unified camera support
 
**Note:** The code automatically detects if it's running on a Raspberry Pi (trying PiCamera first) or another computer (using USB webcam).

## Getting Started

### Modern Python Setup (Recommended)

This version is designed to be **simple and educational** while teaching modern Python practices!

**Why use uv?**
- ✅ Installs modern Python versions (3.14+) easily
- ✅ Manages virtual environments automatically
- ✅ Faster than pip
- ✅ Industry best practice for Python development

**Requirements:**
- Python 3.14+ (we'll install this with uv)
- uv package manager (fast, modern Python tooling)

#### Step 1: Install uv

**On Raspberry Pi / Linux / Mac:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Step 2: Get the Code

```bash
git clone https://github.com/deangoodmanson/MatrixPortalDemos.git
cd MatrixPortalDemos/hs
```

**No `git`?** Download the repo ZIP from GitHub (**Code → Download ZIP**), unzip,
and `cd` into the `hs` folder. In a classroom, your teacher might instead share
the `hs/` folder over a network drive (SMB/NFS), a cloud folder, or a USB stick —
you only need that folder. It contains `pyproject.toml`, which tells `uv` exactly
what to install, so the next step works the same either way.

#### Step 3: Run the Program

No LED matrix hardware is required. The program works with just a webcam — press
`w` to open the preview window and see the LED simulation on screen.

```bash
# From the hs/ folder. On the FIRST run, uv installs Python 3.14 and all
# dependencies (numpy, opencv-python, pyserial, pillow) automatically.
uv run python src/camera_feed.py
```

That's it — no manual virtual environment, no `pip install`, no dependency list
to keep in sync. `uv` reads `pyproject.toml` and sets everything up for you.

**Raspberry Pi Camera Module** (the ribbon-cable camera) needs the system
package, which lives outside the uv environment:

```bash
sudo apt install -y python3-picamera2
# Then run with the system Python so picamera2 is visible:
uv run --python $(which python3) python src/camera_feed.py
```

A plain **USB webcam** needs none of this — `uv run python src/camera_feed.py`
just works, and the code falls back to the USB camera automatically.

### Quick One-Liner Setup

```bash
# Clone and run — uv handles Python and dependencies on first run
git clone https://github.com/deangoodmanson/MatrixPortalDemos.git && \
cd MatrixPortalDemos/hs && \
uv run python src/camera_feed.py
```

#### Recommended Editors

Any editor works, but these free options are especially good for students —
each includes a visual debugger (see [Debugging with VS Code](#debugging-with-vs-code)
below to learn stepping through code line by line):

**Thonny (simplest, great for beginners)**
- Beginner-friendly Python IDE, pre-installed on Raspberry Pi OS
- No terminal knowledge needed; built-in variable inspector and debugger
- Download: [thonny.org](https://thonny.org/) — open `src/camera_feed.py` and press F5

**Visual Studio Code for Education**
- A guided, browser-based version of VS Code built for the classroom — nothing to
  install, runs at [vscodeedu.com](https://vscodeedu.com/)
- Beginner-friendly with built-in coding lessons, then graduates to the same
  VS Code professionals use
- Pairs with the desktop [VS Code](https://code.visualstudio.com/) walkthrough below

**PyCharm Community Edition (full-featured, free)**
- Powerful Python-focused IDE from JetBrains with an excellent visual debugger
- Free Community Edition: [jetbrains.com/pycharm](https://www.jetbrains.com/pycharm/)
- Open the `hs/` folder, then run `src/camera_feed.py`

### Why Learn uv?

**For Students:** uv teaches modern Python practices:
- ✅ **Version management**: Use the right Python for each project
- ✅ **Virtual environments**: Keep projects isolated (no conflicts!)
- ✅ **Fast installs**: uv is 10-100x faster than pip
- ✅ **Industry standard**: Companies use these tools

**Fun fact:** uv is made by Astral, the same team behind Ruff (the super-fast linter used by major Python projects like FastAPI, Pydantic, and hundreds of others!)

## Debugging with VS Code

Visual Studio Code makes it easy to step through your code line by line and see what's happening!

### Step 1: Open the folder in VS Code

```bash
cd hs
uv sync          # creates .venv with all dependencies for the debugger to use
code .
```

Or use File → Open Folder and select `hs`.

### Step 2: Install the Python Extension

1. Click the Extensions icon in the left sidebar (or press `Cmd+Shift+X` on Mac, `Ctrl+Shift+X` on Pi)
2. Search for "Python"
3. Install the one by Microsoft

### Step 3: Select the Python Interpreter

1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Pi) to open the Command Palette
2. Type "Python: Select Interpreter"
3. Choose the one in `.venv/bin/python` (the virtual environment you created)

### Step 4: Create a Debug Configuration

1. Click the Run/Debug icon in the left sidebar (or press `Cmd+Shift+D` / `Ctrl+Shift+D`)
2. Click "create a launch.json file"
3. Select "Python File"

Or create `.vscode/launch.json` manually:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run Camera Feed",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/src/camera_feed.py",
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

### Step 5: Set Breakpoints

Click in the left margin next to any line number to set a red breakpoint dot. The program will pause when it reaches that line!

**Good places to set breakpoints:**
- Line with `frame = capture_frame(...)` - See the captured image
- Line with `small_frame = resize_frame(...)` - See the resized image
- Line with `frame_bytes = convert_to_rgb565(...)` - See the color conversion

### Step 6: Start Debugging

1. Press `F5` or click the green play button
2. The program runs until it hits a breakpoint
3. Use the debug toolbar to:
   - **Continue (F5)** - Run to next breakpoint
   - **Step Over (F10)** - Run one line
   - **Step Into (F11)** - Go inside a function
   - **Step Out (Shift+F11)** - Finish current function

### Step 7: Inspect Variables

When paused at a breakpoint:
- **Variables panel** - See all current variable values
- **Hover over a variable** - See its value
- **Debug Console** - Type variable names to see their values

**Try this:** Set a breakpoint after `small_frame = resize_frame(frame)` and type `small_frame.shape` in the Debug Console to see the image dimensions!

### Troubleshooting VS Code Debugging

**"No module named cv2"**
- Make sure you selected the correct Python interpreter (the one in `.venv`)
- Try: `Cmd+Shift+P` → "Python: Select Interpreter" → choose `.venv`

**"Camera not found" in debug mode**
- Close any other apps using the camera
- The camera can only be used by one program at a time

**Breakpoints not working**
- Make sure you saved the file (`Cmd+S` / `Ctrl+S`)
- Check that "justMyCode" is set to `true` in launch.json

## Learning Path

1. **Read `config.py`** - Understand the settings and constants
2. **Read the top of `camera_feed.py`** - See the overview and how it works
3. **Run the program** - Watch the debug output
4. **Experiment!** - Change DEBUG_MODE, SHOW_PREVIEW, and other settings
5. **Break it on purpose** - See what error messages look like
6. **Fix it** - Learn from the troubleshooting hints

## Key Concepts Covered

- **Digital Images**: How cameras capture pictures as grids of numbers
- **Pixels**: The tiny dots that make up an image
- **RGB Color**: How red, green, and blue combine to make any color
- **Bit Depth**: Why we use RGB565 (16-bit) instead of full color (24-bit)
- **Serial Communication**: How computers talk to hardware devices
- **Loops**: Processing frames one at a time in a while loop
- **Functions**: Organizing code into reusable blocks

## Exercises

### Exercise 1: Change the Matrix Size
Edit `config.py` and change `MATRIX_WIDTH` to 32. What happens to the image?

### Exercise 2: Debug Mode Off
In `camera_feed.py`, change `DEBUG_MODE = False`. How does the output change?

### Exercise 3: Understand RGB565
In the `convert_to_rgb565` function, find where we divide by 8 and by 4. Why is green divided by 4 instead of 8?

### Exercise 4: Add a Color Filter
In the main loop, after capturing a frame, try adding this line:
```python
frame[:, :, 2] = 0  # Remove the red channel
```
What color does the image become?

## Troubleshooting

### "Could not open camera"
- Close other apps that might be using the camera (Zoom, FaceTime)
- Try changing `camera_number` to 1 or 2
- Make sure the webcam is plugged in

### "Matrix Portal not found"
- Plug in the Matrix Portal via USB
- Check that the green power LED is on
- Try unplugging and re-plugging

### Black screen on LED Matrix
- Run the program and watch the debug output
- Make sure you see "Connected successfully!"
- Check that frames are being sent (watch the byte count)

### LEDs are dim or colours look wrong
- Check `MAX_BRIGHTNESS` in `config.py` — it should be `255` for full brightness
- If the Pi randomly resets or flickers when many LEDs are white, lower it to `128`
  (all 2,048 LEDs at full white can draw ~3A; most USB ports only supply 0.5–0.9A)

## Keyboard Controls

Once the program is running, you can use these single-key commands:

**Orientation (Display Direction):**
- `l` = Landscape (wide, horizontal)
- `p` = Portrait (tall, rotates 90°)

**Processing Mode (How Image Fits):**
- `c` = Center (crop from center)
- `s` = Stretch (distort to fit)
- `f` = Fit (letterbox with black bars)

**Effects:**
- `b` = Toggle Black & White / Color
- `m` = Toggle mirror (horizontal flip)
- `z` = Cycle zoom (100% → 75% → 50% → 25%)

**Preview:**
- `w` = Toggle preview window on/off
- `o` = Cycle render algorithm (Gaussian Diffused → Squares → Circles → Gaussian Raw)
- `+` / `=` = Increase LED size (Circles mode only)
- `-` / `_` = Decrease LED size (Circles mode only)

**Actions:**
- `Space` = Snapshot (3-2-1 countdown, saves BMP + PDF)
- `v` = Avatar Capture (guided 18-pose session with voice prompts)

**Demo:**
- `x` = Toggle auto demo mode (cycles through all features)
- `Shift+X` = Start manual demo mode
- `.` or `>` = Next demo step
- `,` or `<` = Previous demo step
- `Space` = Pause/resume auto demo

**System:**
- `t` = Toggle transmission (pause/resume sending to LED matrix, or reconnect)
- `d` = Toggle debug output
- `r` = Reset to defaults
- `h` = Show help
- `q` = Quit

## Next Steps

Once you understand this code, check out the professional version in the `pro/` folder which includes:
- Modular architecture with separate packages (capture, transport, processing, ui)
- Type hints and type checking with ty
- YAML configuration files
- Command-line arguments
- Comprehensive unit test suite
- Better error handling and logging

---

## For Developers / Maintainers

> This section is for developers maintaining the codebase — not for students running it.

### Dev Environment Setup

The `hs/` folder's `pyproject.toml` declares both the runtime dependencies and the
developer tooling. Students just run `uv run python src/camera_feed.py` (uv installs
the runtime deps from it automatically); the commands below add the dev tools.

```bash
cd hs

# Install dev dependencies (ty, ruff) + runtime deps
uv sync

# Activate the venv
source .venv/bin/activate
```

### Type Checking with ty

[ty](https://docs.astral.sh/ty/) is Astral's fast Python type checker (same team as uv and ruff).

```bash
cd hs

# Run type checker
uv run ty check src/

# Expected output (3 warnings are intentional — Pi/Windows-only optional imports):
# warning[unresolved-import]: picamera2  (Pi-only, not installed on Mac)
# warning[unresolved-import]: picamera2  (second usage)
# warning[unresolved-import]: pyttsx3    (Windows TTS, not installed)
# Found 3 diagnostics
```

`ty` is configured in `pyproject.toml`:

```toml
[tool.ty.rules]
unresolved-import = "warn"   # picamera2 and pyttsx3 are optional platform deps
```

### Linting with ruff

```bash
cd hs

# Check for lint issues
uv run ruff check src/

# Format code
uv run ruff format src/
```
