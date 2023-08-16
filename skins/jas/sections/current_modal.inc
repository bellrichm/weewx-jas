##    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<div class="modal" id="currentModal" tabindex="-1" role="dialog" aria-labelledby="currentModalTitle" aria-hidden="true">
    <div class="modal-dialog modal-xl" role="document">
        <div class="modal-content">
            <div class="modal-header" id="currentModalHeader">
                <h5 class="modal-title text-center w-100" id="currentModalTitle"></h5>
                <button type="button" class="close" data-bs-dismiss="modal" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="modal-body" id="currentModalBody">
            #*
                #if $getVar('$Extras.current.observation', False)
                    <h1 id="$Extras.current.observation"></h1>
                #end if
                #if $getVar("$Extras.display_aeris_observation", False)
                    <div id="currentObservation"></div>
                #end if
            *#
                #set i = 0
                <table class="table">
                    <tbody>
                        #for observation in $Extras.current.observations
                            #set i += 1
                            #set valueId = $observation + '_value_modal'
                            #if $i % 2 # <tr class="row mx0"> #end if
                                <th scope="row" class="col" obs_label="$observation"></th>
                                <td id="$valueId" class="col"></td>
                            #if not $i % 2 # </tr> #end if
                        #end for
                    </tbody>
                </table>
                <div id="updateModalDate" class="text-center"></div>
            </div>
            <div class="modal-footer" id="currentModalFooter"></div>
        </div>
    </div>
</div>