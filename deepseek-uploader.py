import os
import subprocess
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PORT = "/dev/ttyUSB0"  # Replace with your actual port (COM3 on Windows)

def generate_code_from_prompt(prompt):
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DeepSeek API key not found in environment variables")
    
    headers = {
        "Authorization": "Bearer {}".format(api_key),
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-coder",
        "messages": [
            {
                "role": "user",
                "content": f"Write ESP32 code for: {prompt}. Provide only the code, no explanations, in a single Arduino .ino file."
            }
        ]
    }
    
    response = requests.post("https://api.deepseek.com/v1/chat/completions", 
                            json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def upload_to_esp32(code, port):
    # Create temporary directory
    os.makedirs("temp_esp32_project", exist_ok=True)
    
    # Write the code to a file
    with open("temp_esp32_project/temp_esp32_project.ino", "w") as f:
        f.write(code)
    
    # Upload using Arduino CLI
    try:
        subprocess.run([
            "arduino-cli", "compile", "--fqbn", "esp32:esp32:esp32", 
            "temp_esp32_project"
        ], check=True)
        
        subprocess.run([
            "arduino-cli", "upload", "-p", port, "--fqbn", "esp32:esp32:esp32", 
            "temp_esp32_project"
        ], check=True)
        
        print("Upload successful!")
    except subprocess.CalledProcessError as e:
        print(f"Upload failed: {e}")
    finally:
        # Clean up
        if os.path.exists("temp_esp32_project/temp_esp32_project.ino"):
            os.remove("temp_esp32_project/temp_esp32_project.ino")
        if os.path.exists("temp_esp32_project"):
            os.rmdir("temp_esp32_project")

if __name__ == "__main__":
    prompt = input("Enter your ESP32 project prompt: ")
    code = generate_code_from_prompt(prompt)
    print("\nGenerated code:\n")
    print(code)
    upload_to_esp32(code, PORT)