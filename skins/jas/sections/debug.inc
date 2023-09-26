##    Copyright (c) 2022 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<button id="connectButton" class="btn btn-primary d-none" type="button" text_label="connect_button_label" onclick="MQTTConnect()"></button>
<button id="disconnectButton" class="btn btn-primary d-none" type="button" text_label="disconnect_button_label" onclick="MQTTDisconnect()"></button>

<div class="col-sm-10 mb-4">
  <button type="button" class="btn btn-primary" onclick="copyLog()">Copy Log</button>
  <button type="button" class="btn btn-primary" onclick="clearLog()">Clear Log</button>
</div>

<div class="col-sm-10 mb-4">
  <div class="text-wrap" id="logDisplay"
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