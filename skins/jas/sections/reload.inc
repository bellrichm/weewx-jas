##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

      <script>
          var current = new Date();
          var future = new Date();
          future.setTime(future.getTime() + 300000); //300000 = 5 minutes 
          var futureTimestamp = Math.floor(future.getTime()/300000) * 300000
          var timeout = futureTimestamp - current.getTime() + 60000

          tdate = new Date(futureTimestamp)
          console.log(current)
          console.log(future)
          console.log(tdate)

          setTimeout(function() { window.location.reload(true); }, timeout);
      </script>