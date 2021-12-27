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
        MQTTConfig = true;

        if(sessionStorage.getItem("header") === null || !MQTTConfig){
            console.log("updating header")
            sessionStorage.setItem("header", JSON.stringify(current.header));
            document.getElementById("$Extras.current.observation").innerHTML = current.header.value + current.header.unit;
        }
        else {
            header = JSON.parse(sessionStorage.getItem("header"));
            document.getElementById("$Extras.current.observation").innerHTML = header.value + header.unit;
        }

        for ([observation, data] of current.observations) {
            suffix = current.suffixes.get(data.suffix);
            if (!suffix){
                suffixText = "";
            }
            else {
                suffixText = " " + suffix.value;
            }

            console.log("updating table");
            document.getElementById(observation + "_label").innerHTML = data.label;
            document.getElementById(observation + "_value").innerHTML = data.value + data.unit + suffixText;
        }   

        // ToDo put here for now
        MQTTConnect();
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