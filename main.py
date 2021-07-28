import netmiko as nk
import requests as rq
import time as tm
import datetime as dt
import threading as td
from tkinter import *
import json

# replace here -- the backend url
urlAPI = 'https://backend-aforo.herokuapp.com/api'

network_token = ''
wlc_mac_list = []
wlc_list = []


headers = {
    'Content-type':'application/json',
    'Accept':'application/json'
}

def network_validation():
    value = network_entry.get()
    if value == '':
        network_result["text"] = "Token incorrecto"
    else:
        response = rq.get(urlAPI + "/networks/" + value)
        if response.status_code == 200:
            global network_token
            network_token = network_entry.get()
            network_name = response.json()['data']['name']
            root.title("Tinkvice SSH: " + network_name)
            network_result["text"] = network_name
            network_entry.delete(0, 'end')
            network_entry["state"] = "disable"
            network_button["state"] = "disable"
            wlc_name_entry["state"] = "normal"
            wlc_mac_entry["state"] = "normal"
            wlc_user_entry["state"] = "normal"
            wlc_ip_entry["state"] = "normal"
            wlc_type_entry["state"] = "normal"
            wlc_psswd_entry["state"] = "normal"
            wlc_validator_button["state"] = "normal"
        elif response.status_code == 400:
            network_result["text"] = "Incorrecto"


def wlc_validation():
    wlc_mac_result["text"] = ""
    wlc_ip_result["text"] = ""
    wlc_type_result["text"] = ""
    wlc_user_result["text"] = ""
    wlc_psswd_result["text"] = ""
    wlc_result["text"] = ""
    name_value = wlc_name_entry.get()
    mac_value = wlc_mac_entry.get()
    ip_value = wlc_ip_entry.get()
    device_value = wlc_type_entry.get()
    user_value = wlc_user_entry.get()
    psswd_value = wlc_psswd_entry.get()
    if mac_value != "":
        wlc_credentials = {
            'ip': ip_value,
            'device_type': device_value,
            'username': user_value,
            'password': psswd_value}
        if mac_value in wlc_mac_list:
            wlc_mac_result["text"] = "Ya ha sido ingresada"
        else:
            try:
                connection = nk.ConnectHandler(**wlc_credentials)
                wlc_result["text"] = "Autenticación correcta"
                wlc_mac_list.append(mac_value)
                wlc_data = {
                    "mac": mac_value,
                    "name": name_value,
                    "connection": connection,
                    "aps": {}
                }
                wlc_list.append(wlc_data)
                wlc_finish_button["state"] = "normal"
            except Exception as e:
                print(e)
                wlc_result["text"] = "Error en la autenticación"
                wlc_ip_result["text"] = "Revisa este campo"
                wlc_type_result["text"] = "Revisa este campo"
                wlc_user_result["text"] = "Revisa este campo"
                wlc_psswd_result["text"] = "Revisa este campo"
    else:
        wlc_mac_result["text"] = "Llena este campo"


def wlc_finish():
    for wlc in wlc_list:
        try:
            rq.post(urlAPI + '/wlcs', json.dumps({
                    'network_id': network_token,
                    'mac': wlc["mac"],
                    'manufacturer_name': 'none',
                    'product_name': wlc["name"]}),headers=headers)
            print(wlc)
            connection = wlc["connection"]
            ap_ssh = connection.send_command("show ap summary")
            ap_summary_lines = ap_ssh.splitlines()[8::1]
            print(ap_summary_lines)
            for item in ap_summary_lines:
                item = item.split()
                try:
                    rq.post(urlAPI + '/aps', json.dumps({
                            'wlc_id': wlc["mac"],
                            'mac': item[3],
                            'name': item[0],
                            'model': item[2],
                            'network_id': network_token}),headers=headers)
                    wlc["aps"][item[3]] = {"date": dt.datetime.now(), "devices": "0", "limit": "0"}
                except Exception as e:
                    print(e)
                    wlc_result["text"] = wlc["name"] + ": Error en la carga de APs"
            init_label.grid(row=12, column=1, columnspan=3)
        except Exception as e:
            print(e)
            wlc_result["text"] = "Error al cargar WLC: " + wlc["name"]


def init_function():
    while True:
        for wlc in wlc_list:
            connection = wlc["connection"]
            try:
                ap_ssh = connection.send_command("show ap summary")
                ap_list = ap_ssh.splitlines()[8::1]
                print("==========================================================")
                for ap in ap_list:
                    ap = ap.split()
                    devic_ssh = ap[8]
                    limit_prev = wlc["aps"][ap[3]]["limit"]
                    try:
                        response = rq.get(urlAPI + '/aps/'+ap[3])
                        limit_app = response.json()['data']['limit']
                        devic_app = response.json()['data']['devices']
                        activ_app = response.json()['data']['active']
                        updateDevices = rq.put(urlAPI + '/aps/' + ap[3] + '/devices', json.dumps({'devices': devic_ssh}),headers=headers)
                        if int(limit_app) <= int(devic_ssh) and activ_app == "0":
                            print('updateActive to 1')
                            saved_date = wlc["aps"][ap[3]]["date"]
                            updateActive = rq.put(urlAPI + '/aps/'+ap[3]+'/active', json.dumps({'active': '1'}),headers=headers)
                            now = dt.datetime.now()
                            date = str(now.day) + "/" + str(now.month) + "/" + str(now.year)
                            hour = str(now.hour) + ":" + str(now.minute) + ":" + str(now.second)
                            response = rq.post(urlAPI + '/alerts', json.dumps({
                                    "network_id": network_token,
                                    "area": ap[0],
                                    "hour": hour,
                                    "date": date,
                                    "device_number": ap[8]}),headers=headers)
                        elif int(limit_app) > int(devic_ssh) and activ_app == "1":
                            updateActive = rq.put(urlAPI + '/aps/'+ap[3]+'/active', json.dumps({'active': '0'}),headers=headers)
                        else:
                            print("====Alerta Enviada====")
                    except Exception as e:
                        print(e)
            except Exception as e:
                print(e)
        tm.sleep(25)


root = Tk()
root.configure(background='#efdad5')
root.geometry("400x330")
root.resizable(False, False)
root.title("Tinkvice SSH")
#root.wm_iconbitmap('./icon.ico')

network_label = Label(root, font="Times 12", text="Ingreso de token de red", background='#efdad5')
network_entry = Entry(root)
network_button = Button(root, text="validar token", command=network_validation, background='#D3B0AE')
network_result = Label(root, font="Times 12 bold", background='#efdad5')

network_label.grid(sticky=W, row=0, column=0, columnspan=3)
network_entry.grid(row=1, column=0, padx=10, pady=3)
network_button.grid(row=1, column=1)
network_result.grid(row=1, column=2)

wlc_label = Label(root, font="Times 12", text="Registro de WLCs", background='#efdad5')
wlc_name_label = Label(root, text="Nombre:", background='#f7f3f1', justify=LEFT)
wlc_mac_label = Label(root, text="MAC:", background='#f7f3f1')
wlc_user_label = Label(root, text="Usuario SSH:", background='#f7f3f1')
wlc_ip_label = Label(root, text="IP:", background='#f7f3f1')
wlc_type_label = Label(root, text="Marca:", background='#f7f3f1')
wlc_psswd_label = Label(root, text="Contraseña SSH:", background='#f7f3f1')

wlc_name_entry = Entry(root)
wlc_mac_entry = Entry(root)
wlc_user_entry = Entry(root)
wlc_ip_entry = Entry(root)
wlc_type_entry = Entry(root)
wlc_psswd_entry = Entry(root, show="*")

wlc_name_result = Label(root, background='#efdad5')
wlc_mac_result = Label(root, background='#efdad5')
wlc_user_result = Label(root, background='#efdad5')
wlc_ip_result = Label(root, background='#efdad5')
wlc_type_result = Label(root, background='#efdad5')
wlc_psswd_result = Label(root, background='#efdad5')

wlc_validator_button = Button(root, text="validar WLC", command=wlc_validation,background='#D3B0AE')
wlc_finish_button = Button(root, text="Iniciar", command=wlc_finish, background='#D3B0AE')

wlc_result = Label(root, background='#efdad5')
wlc_label.grid(sticky=W, row=2, column=0, columnspan=3)
wlc_name_label.grid(sticky=W, row=3, column=0, padx=10, pady=3, ipadx=10)
wlc_name_entry.grid(row=3, column=1)
wlc_name_entry["state"] = "disable"
wlc_name_result.grid(row=3, column=2)
wlc_mac_label.grid(sticky=W, row=4, column=0, padx=10, pady=3, ipadx=10)
wlc_mac_entry.grid(row=4, column=1)
wlc_mac_entry["state"] = "disable"
wlc_mac_result.grid(row=4, column=2)
wlc_user_label.grid(sticky=W, row=5, column=0, padx=10, pady=3, ipadx=10)
wlc_user_entry.grid(row=5, column=1)
wlc_user_entry["state"] = "disable"
wlc_user_result.grid(row=5, column=2)
wlc_ip_label.grid(sticky=W, row=6, column=0, padx=10, pady=3, ipadx=10)
wlc_ip_entry.grid(row=6, column=1)
wlc_ip_entry["state"] = "disable"
wlc_ip_result.grid(row=6, column=2)
wlc_type_label.grid(sticky=W, row=7, column=0, padx=10, pady=3, ipadx=10)
wlc_type_entry.grid(row=7, column=1)
wlc_type_entry["state"] = "disable"
wlc_type_result.grid(row=7, column=2)
wlc_psswd_label.grid(sticky=W, row=8, column=0, padx=10, pady=3, ipadx=10)
wlc_psswd_entry.grid(row=8, column=1)
wlc_psswd_result.grid(row=8, column=2)
wlc_psswd_entry["state"] = "disable"
wlc_validator_button.grid(row=9, column=1, padx=10, pady=3)
wlc_validator_button["state"] = "disable"
wlc_finish_button.grid(row=9, column=2, padx=10, pady=3)
wlc_finish_button["state"] = "disable"
wlc_result.grid(row=10, column=1, columnspan=2)

init_label = Label(root, text="Detectando aglomeraciones", background='#efdad5', command=td.Thread(target=init_function).start())
root.mainloop()
