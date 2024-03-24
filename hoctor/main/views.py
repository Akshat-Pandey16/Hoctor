from django.shortcuts import render
from access_points import get_scanner


from sqlalchemy import create_engine, text
db_str = "mysql+pymysql://ym0a12i67m4ls4f9z9xo:pscale_pw_nm9rVx8r09dPPkqdA2WBkStXkDGfazsZcJeHfyTE4c0@aws.connect.psdb.cloud/localhive?charset=utf8mb4"
db_connection_string = db_str
engine = create_engine(
	db_connection_string,
	connect_args={
        "ssl": {
            "ssl_ca": "/etc/ssl/cert.pem"
        }
    }
)

# Create your views here.
def index(request):
    return render(request, 'landing.html')

# def track2(request):
#     return render(request, 'bitdurg.html')

def home(request):
    li_ssid=[]
    li_security=[]
    li_quality=[]
    a=access()
    for x in range(len(a)):
        li_ssid.append(a[x].ssid)
        li_security.append(a[x].security)
        li_quality.append(a[x].quality)  
    zipped=zip(li_ssid,li_quality,li_security)
    return render(request, 'home.html',{'li':li_ssid,'li_security':li_security,'li_quality':li_quality,'zipped':zipped})    
def access():
    wifi_scanner = get_scanner()
    return(wifi_scanner.get_access_points())


def execute_query(query_string):
	with engine.connect() as conn:
            result = conn.execute(text(query_string))
            print(result)
            return(result.all())
def track(request):
    name_from_html=str(request.POST.get('selected_name'))
    with open('name.txt', 'w') as f:
        f.write(name_from_html)
    li=0
    # import time
    # time.sleep(5)

    import subprocess
    a= subprocess.Popen(['python', 'main/test.py'])
    import time
    time.sleep(5)
    with open('name.txt', 'r') as f:
        result=f.read()
    
    # if(result=='htl_main'):
    #     li=0
    # elif(result=='htl_hack0'):
    #     li=1
    # elif(result=='htl_hashsocietyhome'):
    #     li=1
    # elif(result=='htl_hack1'):
    #     li=2
    # elif(result=='htl_hack2'):
    #     li=3
    # elif(result=='htl_hack3'):
    #     li=4
    # elif(result=='htl_hack4'):
    #     li=5
    # elif(result=='htl_hack5'):
    #     li=5    
    # else:
    #     li=-1
    return render(request, 'tracking.html',{'li':li,'result':result}) 


def track2(request):
    name_from_html=str(request.POST.get('selected_name'))
    print(name_from_html)
    # li=0
    # if(name_from_html == "ranjit"):
    #     li = -1
    # else:
    #     li = 15 
    # with open('name.txt', 'w') as f:
    #     f.write(name_from_html)
    # # import time
    # # time.sleep(5)

    # import subprocess
    # a= subprocess.Popen(['python', 'main/test.py'])
    # import time
    # time.sleep(5)
    # with open('name.txt', 'r') as f:
    #     result=f.read()
    
    # if(result=='entrance_bitd_cse'):
    #     li=0
    # elif(result=='cse_lab01'):
    #     li=1    
    # elif(result=='cse_lab02'):
    #     li=2    
    # else:
    #     li=-1
    return render(request, 'cse.html')


