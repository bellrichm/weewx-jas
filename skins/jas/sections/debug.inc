<input TYPE="button" name="connect" value="Connect" onclick="MQTTConnect()">
<input TYPE="button" name="disconnect" value="Disconnect" onclick="MQTTDisconnect()">
<input TYPE="button" name="copyLog" value="Copy Log" onclick="copyLog()">
<input TYPE="button" name="clearLog" value="Clear Log" onclick="clearLog()">

<div class="col-sm-10">
  <div class="text-wrap" id="jasLog"
    ## style="overflow-y:scroll; width:100%; height:300px">
    style="overflow-y:scroll; height:300px">
  </div>
</div>