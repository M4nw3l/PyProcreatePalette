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
    return (
      self.jsonData['hue'], self.jsonData['saturation'],
      self.jsonData['brightness']
    )

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
    instance = cls()
    lines = value.splitlines()
    counts = [0] * cls.max_rows
    for x in range(len(lines)):
      rowIndex = (x % cls.max_rows)
      while counts[rowIndex] == cls.row_size:
        rowIndex += 1
        if rowIndex == cls.max_rows:
          return instance

      row = cls.hex_regex.findall(lines[x])
      for y in range(len(row)):
        index = rowIndex * cls.row_size + counts[rowIndex]
        if index < cls.max_length:
          instance[index] = Swatch.from_hex(row[y])
          counts[rowIndex] += 1
        else:
          return instance
    return instance


def main():
  palette = None
  paletteFile = None
  paletteString = None

  parser = argparse.ArgumentParser(description='Procreate palette utility')
  commands = parser.add_mutually_exclusive_group()
  commands.add_argument(
    'create',
    nargs='?',
    help='Create Procreate palette from hexadecimal colours'
  )
  commands.add_argument(
    'view', nargs='?', help='Extract and view Procreate palette json file'
  )
  args = parser.parse_args()

  if appex.is_running_extension():
    paletteFile = appex.get_file_path()
    paletteString = appex.get_text()

  if not args.create is None:
    palette = Palette.from_string(paletteString)
    path = os.path.join(tempfile.gettempdir(), palette.name + '.swatches')
    palette.save(path)
    console.open_in(path)
  elif not args.view is None:
    palette = paletteFile and Palette.from_file(paletteFile) or Palette()
    print(palette)
  else:
  	parser.print_help()

if __name__ == "__main__":
  main()

