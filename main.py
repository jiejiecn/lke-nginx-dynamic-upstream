# Works with Linode Kubernetes Engine(LKE) Only!!!
# Modification needed if connect to other provider

from kubernetes import client, config
import json, time
import consul

interval = 2                        #k8s api pull间隔

config_file = "kubeconfig.yaml"     #转发目标集群凭证信息
target_namespace = "namespace"         #转发目标集群namespace

consul_server = "x.x.x.x"     #consul地址，端口默认8500
consul_prefix = "upstream/nginx/"    #consul key前缀，nginx配置中必须匹配相同，不要改

proxy_pass = "{\"weight\":1, \"max_fails\":2, \"fail_timeout\":5}"      #转发策略，一般不用改



config.load_kube_config(config_file)

api = client.CoreV1Api()

while(True):
    try:

        services = api.list_namespaced_service(target_namespace)
        for service in services.items:
            info = json.loads(str(service.metadata.annotations["kubectl.kubernetes.io/last-applied-configuration"]))
            nodePort = info["spec"]["ports"][0]["nodePort"]
            
            #print(json.dumps(info, indent=2))
            #print(nodePort)

        c = consul.Consul(host=consul_server)
        upstream = {}   #upstream dict 

        nodes = api.list_node()

        print("Node Count: ", len(nodes.items))

        for node in nodes.items:
            
            ipAddr = str(node.metadata.annotations["projectcalico.org/IPv4Address"])
            ipAddr = ipAddr.split("/")[0]

            print(node.metadata.name, node.metadata.annotations["projectcalico.org/IPv4Address"])

            key = consul_prefix + ipAddr + ":" + str(nodePort)

            print("Set upstream: ", key, proxy_pass)
            c.kv.put(key, proxy_pass)
            upstream[key] = proxy_pass


        index, data = c.kv.get(consul_prefix, recurse=True)

        for item in data:
            key = item["Key"]
            if upstream.get(key) is None:
                print("Delete upstream: ", key)
                c.kv.delete(key)
        
        time.sleep(interval)
                
    except Exception as ex:
        print("Error: ", ex)        
    finally:
        time.sleep(interval)




