##    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#from weeutil.weeutil import to_bool, to_list

#set global current_modal_global = False
#if $getVar('$Extras.current', False)
  #for observation in $getVar('$Extras.current.observations', {})
      #if 'modal' in to_list($getVar('$Extras.current.observations.' + observation + '.display', ['page', 'modal']))
          #set global current_modal_global = True
          #break
      #end if
  #end for
#end if

    <div class="container">
    #if $getVar('$Extras.pages.' + $page + '.zoomControl', False)
      #include "sections/zoomControl.inc"
    #end if

    #set charts = $getVar('Extras.chart_definitions')
    #set processing_grid = False
    #for $section in $getVar('Extras.pages.' + $page)
      #set include_name = $getVar('Extras.pages.' + $page + '.' + $section + '.filename', None)
      ## ToDo: cleanup to not use continue
      #if not isinstance($Extras.pages[$page][$section],dict)
        #continue
      #end if
      #if not to_bool($getVar('Extras.pages.' + $page + '.' + $section + '.enable', True))
        #continue
      #end if
      #set layout = $getVar('Extras.pages.' + $page + '.' + $section + '.layout', 'grid')
      #if $layout == 'grid' 
        #if not $processing_grid
          #set processing_grid = True
          <div class="row graphrow align-content-start">
        #end if
      #else
        #if processing_grid
          #set processing_grid = False
          </div>
          <div class="row">
        #end if
      #end if
      #set global section_global = $section
      #if $section in $charts
        #include 'sections/chart.inc'
      #else if $include_name is not None
        #include $include_name
      #else
        #include 'sections/' + $section + '.inc'
      #end if
      #set global section_global = None
      #if $layout != 'grid'
        </div>
      #end if
    #end for
    #if $processing_grid
      </div>
    #end if
    </div>
    #if $page_name_global != 'about'
      #set data = '<script src="../charts/' + $page_name_global + '.js"></script>'
      $data
  #end if
    
    <!-- Modal -->
<div class="modal" id="chartModal" tabindex="-1" role="dialog" aria-labelledby="chartModalTitle" aria-hidden="true">
  <div class="modal-dialog modal-xl" role="document">
    <div class="modal-content">
      <div class="modal-header" id="chartModalHeader">
        <h5 class="modal-title" id="chartModalTitle">Modal title</h5>
        <button type="button" class="close" data-bs-dismiss="modal" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
      <div class="modal-body" id="chartModalBody">
        ...
      </div>
      <div class="modal-footer" id="chartModalFooter"></div>
    </div>
  </div>
</div>

#if $current_modal_global
    #include 'sections/current_modal.inc'
#end if