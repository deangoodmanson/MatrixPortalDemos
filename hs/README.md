# High School Learning Version

This folder contains educational versions of the LED Matrix Camera Feed code, designed for high school students learning Python programming.

## What's Different?

Compared to the main `sandbox/` and `pi/` folders, this version has:

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

## Files
 
### src/
Unified version for both macOS and Raspberry Pi:
- `config.py` - Settings with explanations
- `camera_feed.py` - Main program with unified camera support
 
**Note:** The code automatically detects if it's running on a Raspberry Pi (trying PiCamera first) or another computer (using USB webcam).

## Getting Started

### Simple Setup (Recommended for Beginners & Raspberry Pi)

This version is designed to be **simple and educational** - no complex build tools required!

**Requirements:**
- Python 3.9+ (already included with Raspberry Pi OS)
- No uv, no build tools - just basic pip!
- Works with system Python - no need to install Python 3.14

#### On Raspberry Pi (Easiest)

```bash
# 1. Get the files (choose one method):

# Method A: Download directly
cd ~
mkdir ledportal-hs
cd ledportal-hs
wget https://raw.githubusercontent.com/deangoodmanson/MatrixPortalDemos/main/hs/src/camera_feed.py
wget https://raw.githubusercontent.com/deangoodmanson/MatrixPortalDemos/main/hs/src/config.py

# Method B: Clone the whole repo
git clone https://github.com/deangoodmanson/MatrixPortalDemos.git
cd MatrixPortalDemos/hs/src

# 2. Install dependencies (simple pip, no virtual env needed!)
pip3 install opencv-python pyserial numpy pillow

# For Pi Camera support:
sudo apt install -y python3-picamera2

# 3. Run the program
python3 camera_feed.py
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

#### On Mac/Linux (Development Computer)

For testing on your main computer before deploying to Pi:

```bash
cd hs/src

# Create virtual environment (keeps packages isolated)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install opencv-python numpy pyserial pillow

# Run
python camera_feed.py
```

**Note for Advanced Users:** You can use `uv` if you prefer, but it's not required:
```bash
uv venv && source .venv/bin/activate
uv pip install opencv-python numpy pyserial pillow
```

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

## Keyboard Controls

Once the program is running, you can use these single-key commands:

**Orientation (Display Direction):**
- `l` = Landscape (Wide, horizontal)
- `p` = Portrait (Tall, rotates 90°)

**Processing Mode (How Image Fits):**
- `c` = Center (crop from center)
- `s` = Stretch (distort to fit)
- `r` = Fit (letterbox with black bars)

**Effects:**
- `b` = Toggle Black & White / Color

**Tools:**
- `Space` = Snapshot (3-2-1 countdown, saves BMP file)
- `v` = Avatar Capture (guided 18-pose session with voice prompts)
- `d` = Toggle Debug output
- `h` = Show help
- `q` = Quit

## Next Steps

Once you understand this code, check out the professional version in the `pro/` folder which includes:
- Modular architecture with separate modules
- Type hints and type checking
- YAML configuration files
- Command-line arguments
- Comprehensive unit test suite (136 tests)
- Better error handling and logging
