##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.
          
          <div class="col-12 col-xl-6 mb-4">
            <div class="card">
              <div class="card-body text-center">
                <h5 class="card-title"  text_label="radar_title"></h5>
                </h5>
                <div id="radar">
                  <iframe width=100% height=100%
                    #set radar_src ='src="https://embed.windy.com/embed2.html?lat=' + str($station.latitude_f) + '&lon=' + str($station.longitude_f) + '&detail=&detailLat=' + str($station.latitude_f) + '&detailLon=' + str($station.longitude_f) + '&zoom=8&level=surface&overlay=radar&menu=&message=true&marker=&calendar=&pressure=&type=map&location=coordinates&metricWind=&metricTemp=&radarRange=-1"'
                    $radar_src
                    allowfullscreen></iframe>
                </div>
              </div>
            </div>
          </div>
