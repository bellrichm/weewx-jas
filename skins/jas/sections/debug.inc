##    Copyright (c) 2022 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<button id="connectButton" class="btn btn-outline-success d-none" type="button" text_label="connect_button_label" onclick="MQTTConnect()"></button>
<button id="disconnectButton" class="btn btn-outline-success d-none" type="button" text_label="disconnect_button_label" onclick="MQTTDisconnect()"></button>

<input TYPE="button" name="copyLog" value="Copy Log" onclick="copyLog()">
<input TYPE="button" name="clearLog" value="Clear Log" onclick="clearLog()">

<div class="col-sm-10 mb-4">
  <div class="text-wrap" id="jasLog"
    ## style="overflow-y:scroll; width:100%; height:300px">
    style="overflow-y:scroll; height:300px">
  </div>
</div>

<script>
  if (window.self === window.top) {
    document.getElementById('connectButton').classList.remove("d-none");
    document.getElementById('disconnectButton').classList.remove("d-none");
  }
</script> 