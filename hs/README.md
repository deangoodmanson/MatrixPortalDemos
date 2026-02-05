# High School Learning Version

This folder contains educational versions of the LED Matrix Camera Feed code, designed for high school students learning Python programming.

## What's Different?

Compared to the main `sandbox/` and `pi/` folders, this version has:

- **Extensive comments** explaining every section of code
- **Simplified logic** using multiplication/division instead of bit shifting
- **Debug output** showing what's happening at each step
- **Visual preview** windows to see the camera and matrix output
- **Glossary terms** defining technical vocabulary
- **Removed advanced features** (snapshots, command-line arguments)
- **Beginner-friendly error messages** with troubleshooting tips

## Files

### mac/
For macOS computers with a USB webcam:
- `config.py` - Settings with explanations
- `camera_feed.py` - Main program with educational comments

### pi/
For Raspberry Pi with Pi Camera or USB webcam:
- `config.py` - Settings with explanations
- `camera_feed.py` - Main program with Pi-specific camera support

## Getting Started

### Installing Dependencies with uv

We recommend using [uv](https://github.com/astral-sh/uv) by Astral - it's a super fast Python package manager!

#### Step 1: Install uv

**On Mac:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Raspberry Pi / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Step 2: Create a virtual environment and install packages

**On Mac:**
```bash
cd hs/mac
uv venv
source .venv/bin/activate
uv pip install opencv-python numpy pyserial
```

**On Raspberry Pi:**
```bash
cd hs/pi
uv venv
source .venv/bin/activate
uv pip install opencv-python numpy pyserial picamera2
```

#### Step 3: Run the program

**On Mac:**
```bash
cd hs/mac
source .venv/bin/activate
python camera_feed.py
```

**On Raspberry Pi:**
```bash
cd hs/pi
source .venv/bin/activate
python camera_feed.py
```

### Quick Start (if you already have uv installed)

**Mac - one-liner:**
```bash
cd hs/mac && uv venv && source .venv/bin/activate && uv pip install opencv-python numpy pyserial && python camera_feed.py
```

**Raspberry Pi - one-liner:**
```bash
cd hs/pi && uv venv && source .venv/bin/activate && uv pip install opencv-python numpy pyserial picamera2 && python camera_feed.py
```

### Alternative: Using pip directly

If you prefer not to use uv, you can use pip:

```bash
cd hs/mac  # or hs/pi
python3 -m venv .venv
source .venv/bin/activate
pip install opencv-python numpy pyserial
python camera_feed.py
```

## Debugging with VS Code

Visual Studio Code makes it easy to step through your code line by line and see what's happening!

### Step 1: Open the folder in VS Code

```bash
# On Mac
cd hs/mac
code .

# On Raspberry Pi
cd hs/pi
code .
```

Or use File → Open Folder and select `hs/mac` or `hs/pi`.

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

## Next Steps

Once you understand this code, check out the full version in the `sandbox/` and `pi/` folders which includes:
- Snapshot feature (press Enter to save a picture)
- 3-2-1 countdown overlay
- Command-line arguments
- Frame rate limiting options
