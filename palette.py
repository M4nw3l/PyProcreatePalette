import argparse
import os
import re
import sys
import tempfile

import colorsys
from PIL import ImageColor

import json
import zipfile

import appex
import console


class Swatch:
  def __init__(self, jsonData=None):
    self.jsonData = jsonData or {
      'hue': 0.0,
      'saturation': 0.0,
      'brightness': 0.0,
      'alpha': 1,
      'colorSpace': 0
    }

  def __str__(self):
    return str(self.jsonData)

  @property
  def hsv(self):
    return (self.jsonData['hue'], self.jsonData['saturation'],
            self.jsonData['brightness'])

  @hsv.setter
  def hsv(self, value):
    self.jsonData['hue'] = value[0]
    self.jsonData['saturation'] = value[1]
    self.jsonData['brightness'] = value[2]

  @classmethod
  def from_rgb(cls, value):
    instance = cls()
    instance.hsv = colorsys.rgb_to_hsv(*map(lambda v: v / 255, value))
    return instance

  @classmethod
  def from_hex(cls, value):
    if not value.startswith('#'):
      value = '#' + value
    rgb = ImageColor.getcolor(value, 'RGB')
    return cls.from_rgb(rgb)


class Palette:
  max_rows = 3
  row_size = 10
  max_length = max_rows * row_size
  json_file_name = 'Swatches.json'
  json_key_name = 'name'
  json_key_swatches = 'swatches'
  hex_regex = re.compile('(?P<value>#?[A-Fa-f0-9]{2,6})')

  def __init__(self, jsonData=None):
    self.jsonData = jsonData or {
      self.json_key_name: 'Untitled Palette',
      self.json_key_swatches: [None] * self.max_length
    }
    self.jsonSwatches = self.jsonData[self.json_key_swatches]

  def __len__(self):
    return len(self.jsonSwatches)

  def __getitem__(self, index):
    return Swatch(self.jsonSwatches[index])

  def __setitem__(self, index, value):
    self.jsonSwatches[index] = value and value.jsonData

  def __str__(self):
    return str(self.jsonData)

  @property
  def name(self):
    return self.jsonData[self.json_key_name]

  @name.setter
  def name(self, value):
    self.jsonData[self.json_key_name] = value

  def save(self, file):
    jsonString = json.dumps(self.jsonData)
    with zipfile.ZipFile(file, 'w') as zip:
      zip.writestr(self.json_file_name, jsonString)

  @classmethod
  def from_file(cls, file):
    with zipfile.ZipFile(file, 'r').open(cls.json_file_name) as jsonFile:
      jsonData = json.loads(jsonFile)
      return cls(jsonData)

  @classmethod
  def from_string(cls, value):
    instances = []
    instance = cls()
    counts = [0] * cls.max_rows
    lines = value.splitlines()
    for y in range(len(lines)):
      values = cls.hex_regex.findall(lines[y])
      rowIndex = y % cls.max_rows
      for value in values:
        while counts[rowIndex] == cls.row_size and rowIndex < cls.max_rows - 1:
          rowIndex += 1
        index = rowIndex * cls.row_size + counts[rowIndex]
        if index == cls.max_length:
          instances.append(instance)
          instance = cls()
          instance.name += ' ' + len(instances)
          counts = [0] * cls.max_rows
          rowIndex = 0
          index = 0
        instance[index] = Swatch.from_hex(value)
        counts[rowIndex] += 1
    if any(instance.jsonSwatches):
      instances.append(instance)
    return instances


def main():
  paletteFile = None
  paletteString = None

  parser = argparse.ArgumentParser(description='Procreate palette utility')
  commands = parser.add_mutually_exclusive_group()
  commands.add_argument(
    'create',
    nargs='?',
    help='Create Procreate palette (.swatches) files from hex colours')
  commands.add_argument(
    'view',
    nargs='?',
    help='Extract and view json from Procreate palette (.swatches) file')
  parser.add_argument(
    'input', nargs='?', help='.swatches File path or hex values string')
  parser.add_argument(
    'output', nargs='?', help='.json File or .swatches folder output path')
  args = parser.parse_args()

  is_running_extension = False
  if not appex is None and appex.is_running_extension():
    is_running_extension = True
    paletteFile = appex.get_file_path()
    paletteString = appex.get_text()
  else:
    paletteFile = args.input
    paletteString = args.input

  if not args.create is None and not paletteString is None:
    palettes = Palette.from_string(paletteString)
    for palette in palettes:
      path = os.path.join(args.output or tempfile.gettempdir(),
                          palette.name + '.swatches')
      palette.save(path)
      if is_running_extension:
        console.open_in(path)
  elif not args.view is None and not paletteFile is None:
    palette = paletteFile and Palette.from_file(paletteFile) or Palette()
    if args.output is None:
      print(palette)
    else:
      with open(args.output, 'w') as jsonFile:
        jsonFile.write(palette)
  else:
    parser.print_help()


if __name__ == "__main__":
  main()

