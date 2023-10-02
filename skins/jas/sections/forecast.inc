##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

  <div class="col">
    <h5 class="text-center" text_label="forecast_title"></h5>
  </div>
  <div class="row gx-0 justify-content-center">
  #set i = 0
  #for $i in range(7)
    <div class="col col-6 col-sm-4 col-md-3 col-lg-3 col-xl-1 mb-4" style="min-width:9em;">
      <div class="card h-100">
        <div class="card-body text-center">
          <h5 class="card-title">
            <div id="forecastDate$i"></div>
          </h5>
          <div class="card-text" id="forecastObservation$i"></div>
          <div class="card-text" id="forecastTemp$i"></div>
          <div class="card-text" id="forecastRain$i"></div>
          <div class="card-text" id="forecastWind$i"></div>
        </div>
      </div>            
    </div>
    #set i += 1
  #end for
  

