##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<script src="data/current.js"> </script>
<script>
    window.addEventListener("beforeunload", function (event) {
        console.log("before unload")
        if(sessionStorage.getItem("MQTTConnected")){
            MQTTDisconnect()
        }
        alert("before unload")
    })
    window.addEventListener("load", function (event) {
        console.log("foo");

        // ToDo
        MQTTConfig = false;

        if(sessionStorage.getItem("header") === null || !MQTTConfig){
            console.log("updating header")
            sessionStorage.setItem("header", JSON.stringify(current.header));
        }
        header = JSON.parse(sessionStorage.getItem("header"));
        document.getElementById("$Extras.current.observation").innerHTML = header.value + header.unit;

        for ([suffix, data] of current.suffixes) {
            if (sessionStorage.getItem(suffix) === null || !MQTTConfig){
                console.log("updating suffixes")
                sessionStorage.setItem(suffix, JSON.stringify(data));
            }
        }

        for ([observation, data] of current.observations) {
            if (sessionStorage.getItem(observation) === null || !MQTTConfig){
                console.log("updating table");
                sessionStorage.setItem(observation, JSON.stringify(data));
            }
            obs = JSON.parse(sessionStorage.getItem(observation));
           
            suffix = JSON.parse(sessionStorage.getItem(data.suffix));
            if ( suffix=== null) {
                suffixText = "";
            }
            else {
                suffixText = " " + suffix.value;
            }

            document.getElementById(obs.name + "_label").innerHTML = obs.label;
            document.getElementById(obs.name + "_value").innerHTML = obs.value + obs.unit + suffixText;
        }   

        // ToDo, update DateTime dynamically

        // ToDo put here for now
        if (MQTTConfig) {
            MQTTConnect();
        }
    })
</script>
<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
            <h1 id="$Extras.current.observation" class="display-2 indigo-text"></h1>
            #if $getVar("$Extras.display_aeris_observation", False)
                $current_observation['observation']
            #end if
            #set i = 0
                <table class="table">
                  <tbody>
                    #for observation in $Extras.current.observations
                        #set i += 1
                        #set labelId = $observation + '_label'
                        #set valueId = $observation + '_value'
                        #if $i % 2 # <tr> #end if
                            <th id="$labelId" scope="row"></th>
                            <td id="$valueId"></td>
                        #if not $i % 2 # </tr> #end if
                    #end for
                </tbody>
            </table>
            $current.dateTime
        </div>
    </div>
</div>