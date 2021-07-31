#!/bin/bash

gnome-terminal -x sh -c "./${1}"

python3 - << END
import pyautogui 
pyautogui.press(['down', 'up', 'down', 'up', 'down', 'up', 'left', 'right', 'left', 'right', 'left', 'right'])
pyautogui.press('q')
pyautogui.press('y')
END
