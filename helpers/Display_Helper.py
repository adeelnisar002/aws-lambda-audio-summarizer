"""
Helper class for displaying file contents in notebooks.
"""

import os
import json


class Display_Helper:
    """Helper class for displaying file contents."""
    
    def text_file(self, file_path):
        """
        Display the contents of a text file.
        
        Args:
            file_path: Path to the text file
        """
        if not os.path.exists(file_path):
            print(f"The file {file_path} was not found.")
            return
        
        print(f"{file_path}:")
        print("-" * 80)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.strip():
                print(content)
            else:
                print("(File is empty)")
        print("-" * 80)
    
    def json_file(self, file_path):
        """
        Display the contents of a JSON file in formatted form.
        
        Args:
            file_path: Path to the JSON file
        """
        if not os.path.exists(file_path):
            print(f"The file {file_path} was not found.")
            return
        
        print(f"{file_path}:")
        print("-" * 80)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(json.dumps(data, indent=2))
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            # Fall back to text display
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content[:2000])  # Truncate if too long
                if len(content) > 2000:
                    print("\n... (truncated)")
        print("-" * 80)

