from rembg import remove
import easygui
from PIL import Image

inputPath = easygui.fileopenbox(title="Select Image")
outputPath = easygui.filesavebox(title="Save Image")
input = Image.open(inputPath)
output = remove(input)
output.save(outputPath)