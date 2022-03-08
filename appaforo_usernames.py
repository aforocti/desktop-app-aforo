import netmiko as nk
import requests as rq
import time as tm
import datetime as dt
import threading as td
from tkinter import *
import json
import pandas as pd

# replace here -- the backend url
urlAPI = 'https://backend-aforo.herokuapp.com/api'
#urlAPI = 'http://localhost:3000/api'
network_token = ''
wlc_mac_list = []
wlc_list = []
ap_list = []
ap_people = dict()
association_rules = pd.read_csv("association_rules.csv")

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
            root.title("WifiCrowd Spy: " + network_name)
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
    global wlc
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
    wlc = wlc_list[0]
    txt = "Global AP Dot1x EAP Method....................... EAP-FAST"
    try:
        rq.post(urlAPI + '/wlcs', json.dumps({
                'network_id': network_token,
                'mac': wlc["mac"],
                'manufacturer_name': 'none',
                'product_name': wlc["name"]}),headers=headers)
        connection = wlc["connection"]
        ap_ssh = connection.send_command("show ap summary")
        splitlines = ap_ssh.splitlines()
        if txt in splitlines:
            splitlines.remove(txt)
        ap_summary_lines = splitlines[7::1]
        for item in ap_summary_lines:
            item = item.split()
            try:
                rq.post(urlAPI + '/aps', json.dumps({
                        'wlc_id': wlc["mac"],
                        'mac': item[3],
                        'name': item[0],
                        'model': item[2],
                        'network_id': network_token}),headers=headers)
                ap_people[item[0]]= {
                    'mac':  item[3],
                    'people': 0,
                    'clients': []
                }
                wlc["aps"][item[3]] = {"date": dt.datetime.now(), "devices": "0", "limit": "0"}
            except Exception as e:
                print(e)
                wlc_result["text"] = wlc["name"] + ": Error en la carga de APs"
        init_label.grid(row=12, column=1, columnspan=3)
    except Exception as e:
        print(e)
        wlc_result["text"] = "Error al cargar WLC: " + wlc["name"]


def init_function():
    txt = "Global AP Dot1x EAP Method....................... EAP-FAST"
    print("***Starting scanning***")
    command = "show client summary username" 
    id = 1
    while True:
        if(len(wlc_list)>=1):
            wlc = wlc_list[0]
            connection = wlc["connection"]
            prompt = connection.find_prompt()
            try:
                connection.write_channel(f"{command}\n")
                output = ""
                page = ""
                while True:
                    try:
                        page = connection.read_until_pattern(f"More|{prompt}|\n|\t|\s")
                        if "Would you like to display more entries? (y/n)" in page:
                            output += page
                            connection.write_channel("y")
                            #time.sleep(0.075)
                        elif prompt in page:
                            output += page
                            print("****Información recibida*****")
                            break
                    except nk.NetmikoTimeoutException:
                        print("****EXCEPTION*****")
                        break
                
                splitlines = output.splitlines()
                #if txt in splitlines:
                #    splitlines.remove(txt)
                client_list = splitlines[8:-2:1]
                for client in client_list:
                    client = client.split()
                    username = client[3]
                    ap_name = client[1]
                    mac_address = client[0]
                    if username == "N/A":
                        username_rule = association_rules.loc[association_rules['A'] == mac_address]["B"]
                        if(username_rule.shape[0] >= 1):
                            username_rule = association_rules.loc[association_rules['A'] == mac_address]["B"].iloc[0]
                        else:
                            username_rule = "-1"
                        if(username_rule != "-1"):
                            username = username_rule
                            if username not in ap_people[ap_name]['clients']:
                                ap_people[ap_name]['clients'].append(username)
                        else:
                            ap_people[ap_name]['people'] += 1
                    elif username not in ap_people[ap_name]['clients']:
                        ap_people[ap_name]['clients'].append(username)

                for ap in ap_people.keys():
                    ap_mac = ap_people[ap]['mac']
                    #People count
                    #people_number = ap_people[ap]['people']
                    people_number = len(ap_people[ap]['clients']) + ap_people[ap]['people']
                    print("PEOPLE NUMBER: ", people_number)

                    response = rq.get(urlAPI + '/aps/'+ap_mac)
                    limit_app = response.json()['data']['limit']
                    devic_app = response.json()['data']['devices']
                    activ_app = response.json()['data']['active']

                    updateDevices = rq.put(urlAPI + '/aps/' + ap_mac + '/devices', json.dumps({'devices': people_number}),headers=headers)

                    if int(limit_app) <= int(people_number) and activ_app == '0':
                        now = dt.datetime.now()
                        date = str(now.day) + "/" + str(now.month) + "/" + str(now.year)
                        hour = str(now.hour) + ":" + str(now.minute) + ":" + str(now.second)
                        
                        print('Active to 1')
                        updateActive = rq.put(urlAPI + '/aps/'+ap_mac+'/active', json.dumps({'active': '1'}),headers=headers)
                        response = rq.post(urlAPI + '/alerts', json.dumps({
                                "network_id": network_token,
                                "area": ap,
                                "hour": hour,
                                "date": date,
                                "device_number": people_number}),headers=headers)
                    elif int(limit_app) > int(people_number):
                        updateActive = rq.put(urlAPI + '/aps/'+ap_mac+'/active', json.dumps({'active': '0'}),headers=headers)
                    elif int(limit_app) <= int(people_number) and activ_app == '1':
                        print("====Alerta Enviada====")
                    ap_people[ap]['people'] = 0
            except Exception as e:
                print(e)
        else:
            print("SIN WLC")
        try:
            now = dt.datetime.now()
            date = str(now.day) + "/" + str(now.month) + "/" + str(now.year)
            hour = str(now.hour) + ":" + str(now.minute) + ":" + str(now.second)
            ap_ssh = connection.send_command("show client summary username")
            splitlines = ap_ssh.splitlines()[5:]
            line = date + ","+hour+","+",".join(splitlines)+"\n"
            with open("./REPORT_"+wlc["name"]+".txt", "a") as csvfile:
                csvfile.write(line)
        except Exception as e:
            print(e)
        tm.sleep(25)

root = Tk()
root.configure(background='#efdad5')
root.geometry("400x330")
root.resizable(False, False)
root.title("WifiCrowd Spy")
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
