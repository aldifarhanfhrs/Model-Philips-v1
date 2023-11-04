import PySimpleGUI as sg
import time
import base64
from PIL import Image
import io
import socket
import threading
import json
import cv2
import numpy as np

width_display = (1920,1080)
BORDER_COLOR = '#194369'
DARK_HEADER_COLOR = '#112C45'

top_banner = [sg.Column([[
    sg.Text('MCC Vision System Checking', font=('Any 22'), background_color=DARK_HEADER_COLOR, size=(50,1),),
    sg.Text('' , font='Any 22', key='timetext', background_color=DARK_HEADER_COLOR, size=(61,1), justification='R')
]], size=(width_display[0], 50), pad = (0, 0), background_color=DARK_HEADER_COLOR
)]

itemWidth = (width_display[0] - 40) / 3
itemHeight = (width_display[1] - 80) / 2
sizeTitle = (int(itemWidth * 162 / width_display[0]) , 1)
fontTitle = ('Helvetica', 16)
fontText = ('Helvetica', 12)

sizeResult = (int(itemWidth * 122 / width_display[0]) , 1)
fontResult = ('Helvetica', 20)

def get_image64(filename):
    with open(filename, "rb") as img_file:
        image_data = base64.b64encode(img_file.read())
    buffer = io.BytesIO()
    imgdata = base64.b64decode(image_data)
    img = Image.open(io.BytesIO(imgdata))
    new_img = img.resize((800,600))  # x, y
    new_img.save(buffer, format="PNG")
    img_b64 = base64.b64encode(buffer.getvalue())
    return img_b64

imageSample = get_image64("images.jpg")
imageChange = get_image64("images1.png") 

img_b64 = imageSample
  

def createComponet(deviceID): 
    compItem = sg.Column([[sg.T('Font Checking', font= fontTitle, background_color=BORDER_COLOR, size=sizeTitle, justification='c', pad = (0,0))], 
        [sg.T(deviceID + ':', font= fontText, background_color=DARK_HEADER_COLOR),
          sg.Input(sg.user_settings_get_entry('-dev1-', ''), key='-dev1-', size=(15, 1), font= fontText),
          sg.B('update', key='updDev1', font= fontText), 
          sg.T('Enable'  + ' ' * 6 + ':', font= fontText, background_color=DARK_HEADER_COLOR, pad = ((30,0),(0,0))),
          sg.CB('enable Device', font=fontText, enable_events=True, k='-enableDev-', background_color=DARK_HEADER_COLOR, default=sg.user_settings_get_entry('-enableDev-', ''))
        ], [sg.T('Result', font= fontResult, background_color=DARK_HEADER_COLOR, size=sizeResult, justification='c', pad = (0,0))],
        [sg.Image(data=img_b64, pad=(0, 0), key='image' + deviceID)]
      ],size=(itemWidth, itemHeight), background_color=DARK_HEADER_COLOR, pad = ((10, 0), (10, 0)))
    
    if deviceID == "config":
        compItem = sg.Column([[sg.Text('Column2', background_color='green', size=(50,20)),
                               sg.Button('capture', button_color=('white', 'firebrick3'))                               
                            ]],
                size=(itemWidth, itemHeight), background_color=DARK_HEADER_COLOR, pad = ((10, 0), (10, 0)))
     
    return compItem

#contTop = [frontItem, leftItem, rightItem]
deviceList = ('1', '2', '3')
contTop = [createComponet(deviceName) for deviceName in deviceList]

deviceList1 = ('4', '5', 'config')
contButtom = [createComponet(deviceName) for deviceName in deviceList1]

layout = [top_banner, contTop, contButtom]

window = sg.Window('MCC Visual Inspection',
                layout, finalize=True,
                resizable=True,
                no_titlebar=True,
                margins=(0, 0),
                grab_anywhere=True,
                location=(0, 0), right_click_menu=sg.MENU_RIGHT_CLICK_EDITME_VER_EXIT)

# Create a TCP/IP socket
ServerSocket = socket.socket()
host = '0.0.0.0'
port = 5000
try:
    ServerSocket.bind((host, port))
except socket.error as e:
    print(str(e))
ServerSocket.listen()

captureRequest = 0

def recvall(sock):
    BUFF_SIZE = 4096 # 4 KiB
    data = b''
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    return data

def on_new_client(client_socket, addr):
  thread = threading.Thread(target=sendData, args=(client_socket, addr))  # create the thread
  thread.start()  #

  dataAll = recvall(client_socket)
  dataJson = json.loads(dataAll)
  deviceID = str(dataJson["data"]["deviceID"])
  my_bytes = dataJson["data"]["imageRaw"]
  imgbytes = base64.b64decode(my_bytes)
  
  #change image size
  base64Data = base64.b64encode(imgbytes)
  decoded_data = base64.b64decode(base64Data)
  np_data = np.fromstring(decoded_data,np.uint8)
  img = cv2.imdecode(np_data,cv2.IMREAD_UNCHANGED)
  imgbytesSend = cv2.imencode('.png', cv2.resize(img, (650,400)))[1].tobytes()  # ditto
  dataImage = base64.b64encode(imgbytesSend).decode('ascii')

  window['image' + deviceID].update(data=dataImage)
  time.sleep(0.05)   

    
    
  client_socket.close()
  thread.join()

def sendData(client_socket, addr):  
  checkData = 0
  print(addr[0])
  while True:
    time.sleep(0.05)
    if checkData != captureRequest:
      try:
        checkData = captureRequest
        datajson = {"request" : "checking"}
        sendJson = json.dumps(datajson)
        client_socket.sendall(sendJson.encode())
        print("changeData")
      except:
         print("disconnect")
         break

def s_changes():
  while True:
    Client, address = ServerSocket.accept()
    print('Connected to: ' + address[0] + ':' + str(address[1]))
    thread = threading.Thread(target=on_new_client, args=(Client, address))  # create the thread
    thread.start()  # start the thread

thread = threading.Thread(target=s_changes)
thread.daemon = True
thread.start()

while True:    
  window['timetext'].update(time.strftime('%H:%M:%S'))
  event, values = window.read(timeout=50)
  if event in (sg.WINDOW_CLOSED, 'Exit'):
      break    
  elif event == 'capture':
      captureRequest = captureRequest + 1
      print(captureRequest)
window.close()