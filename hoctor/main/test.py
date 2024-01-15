import os
from whereami.predict import * 
import pickle
######################################################################
import pyrebase

#setting up firebase
firebaseConfig={"apiKey": "AIzaSyD6jD0sTnnixvMhv_3us1uCzqS4oIibiCY","authDomain": "localhive-8693c.firebaseapp.com","projectId": "localhive-8693c","storageBucket": "localhive-8693c.appspot.com","messagingSenderId": "561721796855","appId": "1:561721796855:web:848a3d4bafc1c4ea098bf2","measurementId": "G-BK10KQ0P12","databaseURL": ""}

firebase=pyrebase.initialize_app(firebaseConfig)

#define storage
storage=firebase.storage()



#get url of the file we just uploaded
# print(storage.child(cloudfilename).get_url(None))

# #download a file
# storage.child(cloudfilename).download("downloaded.txt")


# #to read from the file
# path=storage.child(cloudfilename).get_url(None)
# f = urllib.request.urlopen(path).read()
# print(f)
################################################################
def access():
    wifi_scanner = get_scanner()
    aps = wifi_scanner.get_access_points()
    print(type(aps[0]))

    data = aps
    with open("my_obj.dat", "wb") as f:
        pickle.dump(data, f)
    # print(len(aps))
    #upload a file
    file="my_obj.dat"
    cloudfilename="yash.dat"
    storage.child(cloudfilename).put(file)


data=[]
#access()
##Download###
with open('name.txt', 'r') as f:
        name=f.read()
print(name)
# cloudfilename=f"{name}.dat"
# storage.child(cloudfilename).download(f"{ name }.dat")

cloudfilename = f"{name}.dat"
localfilename = f"{name}.dat"
storage.child(cloudfilename).download(localfilename)
with open(f"{name}.dat", "rb") as f:
    loaded_obj = pickle.load(f)
#print(type(loaded_obj))
print(type(loaded_obj[0]))

f.close()
print(loaded_obj)
a=predict( loaded_obj,input_path=None ,model_path=None, device="")
with open('name.txt', 'w') as f:
        f.write(a)