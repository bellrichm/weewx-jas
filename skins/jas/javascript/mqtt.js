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
}

function onConnectionLost(responseObject) {
    console.log("onConnectionLost: Connection Lost");
    if (responseObject.errorCode !== 0) {
        console.log("onConnectionLost: " + responseObject.errorMessage);
    }
}

function onFailure(message) {
    console.log("Failed: " + message);
}

function onMessageArrived(message) {
    console.log("onMessageArrived: " + message.payloadString);
    var test_obj = JSON.parse(message.payloadString);
    document.getElementById("dateTime").innerHTML = test_obj.dateTime;
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
