//    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
//    See the file LICENSE.txt for your rights.

var client;
var host="weather-data.local";
var port=9001;
var clientID = "clientID-" + parseInt(Math.random() * 100);
var topic = "weather/loop";

function onConnect() {
    console.log(" in onConnect");
    client.subscribe(topic);
}

function onConnected(reconn ,url){
	console.log(" in onConnected " + reconn);
    sessionStorage.setItem("MQTTConnected", true);
}

function onConnectionLost(responseObject) {
    console.log("onConnectionLost: Connection Lost");
    sessionStorage.removeItem("MQTTConnected");
    if (responseObject.errorCode !== 0) {
        console.log("onConnectionLost: " + responseObject.errorMessage);
    }
}

function onFailure(message) {
    console.log("Failed: " + message);
}

function onMessageArrived(message) {
    //console.log("onMessageArrived: " + message.payloadString);
    //console.log("  onMessageArrived: " + (Date.now()/1000));
    console.log("  onMessageArrived: ");
    var test_obj = JSON.parse(message.payloadString);
    header = JSON.parse(sessionStorage.getItem("header"));
    if (test_obj[header.name]) {
        header.value = test_obj[header.name];
        if (test_obj[header.unit]) {
            header.unit = test_obj[header.unit];
        }
        sessionStorage.setItem("header", JSON.stringify(header));
        document.getElementById(header.name).innerHTML = header.value + header.unit;
    }
    
    suffixes = sessionStorage.getItem("suffixes").split(",");
    suffixes.forEach(function(suffix) {
        //console.log(suffix);
        if (test_obj[suffix]) {
            data = JSON.parse(sessionStorage.getItem(suffix));
            data.value = test_obj[suffix];
            sessionStorage.setItem(suffix, JSON.stringify(data));
        }    
    });

    observations = sessionStorage.getItem("observations").split(",");
    observations.forEach(function(observation) {
        //console.log(observation);
        if (test_obj[observation]) {
            data = JSON.parse(sessionStorage.getItem(observation));
            data.value = test_obj[observation];
            sessionStorage.setItem(observation, JSON.stringify(data));

            suffix = JSON.parse(sessionStorage.getItem(data.suffix));
            if ( suffix=== null) {
                suffixText = "";
            }
            else {
                suffixText = " " + suffix.value;
            }

            document.getElementById(observation + "_label").innerHTML = data.label;
            document.getElementById(data.name + "_value").innerHTML = data.value + data.unit + suffixText;
        }
    });    
    
    if (test_obj.dateTime) {
        sessionStorage.setItem("updateDate", test_obj.dateTime*1000);
        var dateTime = new Date(test_obj.dateTime*1000);
        // ToDo, use server locale not the browser so have correct timezone? 
        document.getElementById("updateDate").innerHTML = dateTime.toLocaleString();
    }    

    //console.log("done");
}

function MQTTConnect() {
    console.log(" in MQTTConnect");
    client = new Paho.MQTT.Client(host, Number(port), clientID);

    client.onConnectionLost = onConnectionLost;
    client.onMessageArrived = onMessageArrived;
    client.onConnected = onConnected;

    client.connect({ 
        timeout: 30,
        keepAliveInterval: 60,
        cleanSession: true,
        useSSL: false,
        reconnect: true,
        // end defaults
        //userName: "",
        //password: "",
		onSuccess: onConnect,
		onFailure: onFailure,        
    });
}

function MQTTDisconnect() {
    console.log(" in MQTTDisconnect");
    client.disconnect();
}
