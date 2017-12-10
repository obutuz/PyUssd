import falcon
import requests
import pickle


def display_response(response,choice_error_message=None,response_data_len=None):
  

    controls="\n00: Home \n0: Previous"
    
    display=response.get("message")
    if choice_error_message:
        display="CON "+choice_error_message
    
    for m in response.get('menus'):
       

        if m.get('id')=='0':
            display+='\n'+"%s"%(m.get('label'))
        else:
            display+='\n'+"%s: %s"%(m.get('id'),m.get('label'))

    if response_data_len==1:
        display='\n'+display
    else:
        display='\n'+display+controls
    return display


def make_http_request(url,params,session):
    response_data_list=None
    request=requests.post(url=url,json=params) #call external
    response=request.json()
    
    if session:
        response_data_list=session.get('response_data_list')
        response_data_list.append(response)
        session.update({"session_id":params.get('session_id'),"response_data_list":response_data_list})
    else:
        response_data_list=[response]
        session={"session_id":params.get('session_id'),"response_data_list":response_data_list}
    return (session,response,)

                

class UssdResource:
    def on_get(self,req,resp):
        msisdn=req.params.get('msisdn')
        session_id=req.params.get('session_id')
        ussd_string=req.params.get('ussd_string')
        ussd_choice_list=None
        ussd_choice=None
        endpoint_url=self.service_endpoint

        if ussd_string:
            ussd_choice_list=str(ussd_string).split('*')
        else:
            ussd_choice_list=[]

        if len(ussd_choice_list)>1:
            ussd_choice=ussd_choice_list[-1]
        elif len(ussd_choice_list)==1:
            if str(self.service_sub_code)!=ussd_choice_list[0]:
                ussd_choice=ussd_choice_list[0]
        

        #get session info
        session=self.redis.get(self.service_session_key)
       
        #sample request to client API
        request_data={'operator_session_id':session_id,
                      'msisdn':msisdn,
                      'choice':ussd_choice,
                      "info":{},
                      "client_session":{},
                      }
    
        #sample response from client API
        
        display=None

        if session:
            p_session=pickle.loads(session)
            choice=request_data.get('choice')
            response_data_list=p_session.get('response_data_list')

            if choice=='0':
                #previous
                response=response_data_list[-2] #get previous
                response_data_list=response_data_list[:-1]
                p_session.update({"session_id":session_id,"response_data_list":response_data_list})
                resp.body=display_response(response,response_data_len=len(response_data_list))
            elif choice=='00':
                response=response_data_list[0] #get initial display
                response_data_list=[response]
                p_session.update({"session_id":session_id,"response_data_list":response_data_list})
                resp.body=display_response(response,response_data_len=len(response_data_list))
            else:
                #print (response_data_list)

                prev_response=response_data_list[-1] #get last element. do not use pop here
                #get the link
                #print (prev_response)

                prev_menus=prev_response.get("menus")

                menu_d=None
            
                for menu in prev_menus:
                    print (choice,menu.get('id'))
                    if choice==menu.get('id'):
                        #call external with this
                        menu_d=menu
                        break
                
                #call if available
                if not menu_d:
                    #no choice made
                    resp.body=display_response(prev_response,choice_error_message="Incorrect Input")
                else:
                    url=prev_response.get("url",endpoint_url)
                    client_session=prev_response.get('client_session')
                    info=menu_d.get("info")
                    request_data.update({"info":info,"client_session":client_session})

                    p_session,response=make_http_request(url,request_data,p_session)
                    resp.body=display_response(response)
        else:
            url=endpoint_url
            p_session,response=make_http_request(url,request_data,None)
            #assign for display
            resp.body=display_response(response,response_data_len=0)

            
        #update or se session
        self.redis.set(self.service_session_key,pickle.dumps(p_session))
        
    
       



        
