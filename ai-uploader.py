import os
from esptool import main as esptool_main
import serial
from serial.tools import list_ports
import openai
from pathlib import Path
import time
import subprocess
from dotenv import load_dotenv

def load_config():
    """Load configuration based on environment"""
    load_dotenv()
    
    config = {
        'api_key': os.getenv('OPENAI_API_KEY'),
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'model': os.getenv('OPENAI_MODEL', 'gpt-4'),
        'board_type': os.getenv('ESP32_BOARD', 'esp32:esp32:esp32'),
    }
    
    return config

class ESP32AIUploader:
    def __init__(self):
        # Load configuration
        config = load_config()
        self.api_key = config['api_key']
        self.model = config['model']
        self.board_type = config['board_type']
        
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not found. Please ensure you have:\n"
                "1. Created a .env file\n"
                "2. Added OPENAI_API_KEY=your_api_key to the .env file\n"
                "3. Or set it as an environment variable"
            )
        
        if not self._validate_api_key(self.api_key):
            raise ValueError("Invalid OpenAI API key format")
        
        openai.api_key = self.api_key
        self.sketches_dir = Path("./esp32_sketches")
        self.sketches_dir.mkdir(exist_ok=True)

    def _validate_api_key(self, api_key):
        """Basic validation of API key format"""
        # OpenAI API keys typically start with 'sk-' and are 51 characters long
        return isinstance(api_key, str) and api_key.startswith('sk-') and len(api_key) == 51

    def find_esp32_port(self):
        """Automatically detect ESP32 port"""
        try:
            ports = list_ports.comports()
            for port in ports:
                if "CP210X" in port.description.upper() or "CH340" in port.description.upper():
                    return port.device
            return None
        except Exception as e:
            print(f"Error detecting ESP32 port: {e}")
            return None

    def generate_sketch(self, prompt):
        """Generate Arduino sketch using AI"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert in ESP32 Arduino programming. Generate only the code without explanations."
                    },
                    {
                        "role": "user", 
                        "content": f"Generate Arduino sketch for ESP32: {prompt}"
                    }
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating sketch: {e}")
            return None

    def save_sketch(self, sketch_content, prompt):
        """Save sketch to file"""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"sketch_{timestamp}.ino"
            filepath = self.sketches_dir / filename
            
            with open(filepath, 'w') as f:
                f.write(f"// Generated from prompt: {prompt}\n")
                f.write(f"// Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"// Board type: {self.board_type}\n\n")
                f.write(sketch_content)
            
            return filepath
        except Exception as e:
            print(f"Error saving sketch: {e}")
            return None

    def compile_and_upload(self, sketch_path):
        """Compile and upload sketch to ESP32"""
        try:
            port = self.find_esp32_port()
            if not port:
                raise ValueError("ESP32 port not found")

            # Ensure Arduino CLI is installed and configured for ESP32
            print("Compiling sketch...")
            compile_cmd = [
                "arduino-cli", "compile",
                "--fqbn", self.board_type,
                str(sketch_path)
            ]
            subprocess.run(compile_cmd, check=True)
            
            print("Uploading to ESP32...")
            upload_cmd = [
                "arduino-cli", "upload",
                "-p", port,
                "--fqbn", self.board_type,
                str(sketch_path)
            ]
            subprocess.run(upload_cmd, check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error during compilation/upload: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

def verify_environment():
    """Verify all required environment variables and dependencies"""
    missing = []
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        missing.append("OPENAI_API_KEY")
    
    # Check for Arduino CLI
    try:
        subprocess.run(["arduino-cli", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Arduino CLI not found. Please install it first.")
        return False
    
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        return False
    
    return True

def main():
    # Verify environment before starting
    if not verify_environment():
        return
    
    try:
        uploader = ESP32AIUploader()
        
        # Find ESP32 port
        port = uploader.find_esp32_port()
        if not port:
            print("No ESP32 device found. Please connect your device.")
            return

        print(f"Found ESP32 at port: {port}")
        
        while True:
            try:
                prompt = input("\nEnter your prompt (or 'quit' to exit): ")
                if prompt.lower() == 'quit':
                    break

                print("Generating sketch...")
                sketch_content = uploader.generate_sketch(prompt)
                
                if sketch_content:
                    sketch_path = uploader.save_sketch(sketch_content, prompt)
                    if sketch_path:
                        print(f"Sketch saved to: {sketch_path}")
                        
                        upload = input("Would you like to upload this sketch? (y/n): ")
                        if upload.lower() == 'y':
                            print("Uploading sketch...")
                            if uploader.compile_and_upload(sketch_path):
                                print("Upload complete!")
                            else:
                                print("Upload failed. Please check the error messages above.")
                    else:
                        print("Failed to save sketch.")
                else:
                    print("Failed to generate sketch.")
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                continue

    except Exception as e:
        print(f"Critical error: {e}")
        return

if __name__ == "__main__":
    main()
