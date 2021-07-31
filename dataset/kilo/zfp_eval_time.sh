#!/bin/bash


gnome-terminal -x sh -c "./${1} $(pwd)/storage/final-dataset/kilo/README.md"

python3 - << END
import pyautogui 
pyautogui.press('enter')
pyautogui.press('enter')
pyautogui.press(['up', 'up'])
pyautogui.write('Zero Footprint Opaque Predicates Are Awesome!', interval=0.25)
pyautogui.press(['down'])
pyautogui.write('- Jerry', interval=0.25)
pyautogui.keyDown('ctrl')
pyautogui.press('s')
pyautogui.press('q')
pyautogui.keyUp('ctrl')
END
