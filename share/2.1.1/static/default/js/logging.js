require(["jquery", "jhapi"], function (
    $,
    JHAPI,
  ) {
    "use strict";
  
    var base_url = window.jhdata.base_url;
    var api = new JHAPI(base_url);
  
  
    // Get LoggingHandler infos on page load
    $(document).ready(function () {
      // Jupyterhub
      var jhub_handlers = {"file": null, "stream": null, "smtp": null, "syslog": null}
  
      api.api_request("logs/handler", {
        success: function (config) {
          // For each handler
          for (const handler in config) {
            // get all configurations options
            for (const c in config[handler]) {
              var element = $(`#jhub-${handler}-${c}`);
              // and set the value in the correspoding html element
              element.val(config[handler][c]);
            }
            jhub_handlers[handler] = config[handler];
          }
  
          // Can only create those handlers which do not exist
          for (const handler in jhub_handlers) {
            if (!jhub_handlers[handler]) {
              $(`#jhub-${handler}-patch, #jhub-${handler}-delete`).addClass("disabled");
              // Empty all settings
              $(`#jhub-${handler}-settings`).find("select, input").each(function() {
                $(this).val('');
              })
            } else {
              $(`#jhub-${handler}-create`).addClass("disabled");
            }
          }
        }
      })
    });
  
    function create_handler() {
      var handler = $(this).attr("id").split('-')[1];
      var output_area = $(`#jhub-${handler}-alert`);
  
      var settings = $("#jhub-log-settings-collapse");
      var config = {};
      $(`#jhub-${handler}-settings`).find("select, input").each(function() {
        var value = $(this).val();
        var setting = $(this).attr("id").split('-')[2];
        config[setting] = value;
      })
  
      api.api_request("logs/handler/" + handler, {
        type: "POST",
        data: JSON.stringify(config),
        success: function (data, textStatus) {
          output_area.text(textStatus);
        },
        error: function (xhr, textStatus, errorThrown) {
          output_area.text(`Error: ${xhr.status} ${errorThrown}`);
        }
      })
    }
  
    function delete_handler() {
      var handler = $(this).attr("id").split('-')[1];
      var output_area = $(`#jhub-${handler}-alert`);
      api.api_request("logs/handler/" + handler, {
        type: "DELETE",
        success: function (data, textStatus) {
          output_area.text(textStatus);
          console.log(response)
        },
        error: function (xhr, textStatus, errorThrown) {
          output_area.text(`Error: ${xhr.status} ${errorThrown}`);
        }
      })
    }
  
    $("button[id^=jhub][id$=create]").click(create_handler);
    $("button[id^=jhub][id$=delete]").click(delete_handler);
  
  });