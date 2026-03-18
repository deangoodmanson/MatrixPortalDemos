# High School Learning Version

This folder contains educational versions of the LED Matrix Camera Feed code, designed for high school students learning Python programming.

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
# Method A: Clone the repository (recommended)
git clone https://github.com/deangoodmanson/MatrixPortalDemos.git
cd MatrixPortalDemos/hs/src

# Method B: Download just the files you need
mkdir ~/ledportal-hs
cd ~/ledportal-hs
wget https://raw.githubusercontent.com/deangoodmanson/MatrixPortalDemos/main/hs/src/camera_feed.py
wget https://raw.githubusercontent.com/deangoodmanson/MatrixPortalDemos/main/hs/src/config.py
```

#### Step 3: Install Python and Dependencies

```bash
# uv will automatically install Python 3.14 and create a virtual environment!
uv venv

# Activate the virtual environment
source .venv/bin/activate  # Mac/Linux
# OR on Windows: .venv\Scripts\activate

# Install dependencies
uv pip install opencv-python pyserial numpy pillow

# On Raspberry Pi, also install Pi Camera support:
sudo apt install -y python3-picamera2
uv pip install picamera2
```

#### Step 4: Run the Program

No LED matrix hardware is required. The program works with just a webcam — press
`w` to open the preview window and see the LED simulation on screen.

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Run!
python camera_feed.py
```

### Quick One-Liner Setup

```bash
# Clone, create venv, install deps, and run (all in one!)
git clone https://github.com/deangoodmanson/MatrixPortalDemos.git && \
cd MatrixPortalDemos/hs/src && \
uv venv && source .venv/bin/activate && \
uv pip install opencv-python pyserial numpy pillow && \
python camera_feed.py
```

#### Pi-Friendly Editors

**Thonny (Recommended for Students)**
- Pre-installed on Raspberry Pi OS
- Beginner-friendly with visual debugger
- No terminal knowledge needed

```bash
# Open in Thonny
thonny camera_feed.py
# Click the green "Run" button or press F5
```

**nano (Quick Terminal Edits)**
```bash
nano camera_feed.py
# Edit, Ctrl+O to save, Ctrl+X to exit
python3 camera_feed.py
```

**VS Code (Advanced)**
```bash
code camera_feed.py
```

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
cd hs/src
code .
```

Or use File → Open Folder and select `hs/src`.

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
            "program": "${workspaceFolder}/camera_feed.py",
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
- Comprehensive unit test suite (187 tests)
- Better error handling and logging

---

## For Developers / Maintainers

> This section is for developers maintaining the codebase — not for students running it.

### Dev Environment Setup

The `hs/` folder has a `pyproject.toml` for developer tooling (type checking, linting).
Students use the manual `uv pip install` approach in `hs/src/` — this is the developer setup.

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
