import pyautogui
import ollama
from PIL import Image, ImageDraw, ImageFont
import time
import os

# CONFIGURATION
MODEL_NAME = "llama3.2-vision"  # Must have this pulled in Ollama
GRID_ROWS = 4
GRID_COLS = 4

def add_grid_overlay(screenshot_path, output_path):
    """Draws a numbered grid on the screenshot for the AI to reference."""
    image = Image.open(screenshot_path)
    draw = ImageDraw.Draw(image)
    width, height = image.size
    cell_w = width / GRID_COLS
    cell_h = height / GRID_ROWS
    
    centers = {} # Store center (x,y) for each grid number
    
    count = 1
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            # Calculate coordinates
            left = c * cell_w
            top = r * cell_h
            right = left + cell_w
            bottom = top + cell_h
            center_x = left + (cell_w / 2)
            center_y = top + (cell_h / 2)
            
            # Draw box
            draw.rectangle([left, top, right, bottom], outline="red", width=2)
            
            # Draw number
            # Using default font for simplicity; in prod use a large TTF font
            draw.text((left + 5, top + 5), str(count), fill="red")
            
            centers[count] = (center_x, center_y)
            count += 1
            
    image.save(output_path)
    return centers

def get_ai_action(grid_image_path, user_goal):
    """Sends the grid image to local Llama 3.2 Vision."""
    print(f"🤖 Thinking about goal: '{user_goal}'...")
    
    prompt = f"""
    You are controlling a computer. The user wants to: "{user_goal}".
    The screen is divided into a grid numbered 1 to {GRID_ROWS * GRID_COLS}.
    
    1. Identify the single most relevant grid number to click to achieve the goal.
    2. Respond with ONLY the grid number. Nothing else.
    """
    
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [grid_image_path]
            }]
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"Error: {e}"

def main():
    user_goal = pyautogui.prompt(text='What should the agent do?', title='Local Agent Goal')
    if not user_goal:
        return

    # 1. capture screen
    print("📸 Taking screenshot...")
    screenshot = pyautogui.screenshot()
    screenshot.save("screen.png")

    # 2. Apply Grid (Set-of-Mark)
    centers = add_grid_overlay("screen.png", "screen_grid.png")
    
    # Show the user the grid (Optional debug)
    # Image.open("screen_grid.png").show()

    # 3. Get Decision from AI
    grid_choice = get_ai_action("screen_grid.png", user_goal)
    print(f"🤖 AI suggests clicking Grid #{grid_choice}")

    # 4. Clean up response (AI might say "Grid 5" instead of just "5")
    try:
        choice_int = int(''.join(filter(str.isdigit, grid_choice)))
        target_x, target_y = centers[choice_int]
    except:
        print(f"❌ Could not interpret AI response: {grid_choice}")
        return

    # 5. Human-in-the-loop Safety Latch
    confirm = pyautogui.confirm(
        text=f"AI wants to CLICK Grid #{choice_int}\n(Coordinates: {int(target_x)}, {int(target_y)})\n\nGoal: {user_goal}",
        title='Safety Check',
        buttons=['Approve', 'Deny']
    )

    if confirm == 'Approve':
        print(f"🖱️ Clicking {target_x}, {target_y}...")
        pyautogui.click(target_x, target_y)
        print("✅ Action Complete.")
    else:
        print("🛑 Action Denied by User.")

if __name__ == "__main__":
    main()