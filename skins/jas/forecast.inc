##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

    <div class="col">
      $gettext["forecast.title"]
    </div>
  </div>
  <div class="row gx-0 justify-content-center">
  #for $forecast in $forecasts
    <div class="col col-6 col-sm-4 col-md-3 col-lg-3 col-xl-1" style="min-width:9em;">
      <div class="card h-100">
        <div class="card-body text-center">
          <h5 class="h5-responsive indigo-text">
            $forecast['day'] $forecast['date']
          </h5>
          <div class="card-text">$forecast['observation']</div>
          <div class="card-text">$forecast['min_temp'] | $forecast['max_temp']</div>
          <div class="card-text"><i class="wi wi-raindrop"></i> $forecast['rain']%</div>
          <div class="card-text"><i class="wi wi-strong-wind"></i> $forecast['min_wind'] | $forecast['max_wind'] mph</div>
        </div>
      </div>            
    </div>
  #end for
  

