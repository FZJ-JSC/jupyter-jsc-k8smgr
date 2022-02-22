// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

require(["jquery", "jhapi", "utils"], function (
  $,
  JHAPI,
  utils
) {
  "use strict";

  var base_url = window.jhdata.base_url;
  var user = window.jhdata.user;
  var api = new JHAPI(base_url);


  /*
  Listen for new pending spawner notifications
  */
  var update_url = utils.url_path_join(jhdata.base_url, "api/users", user, "notifications", "spawners");
  var evtSource = new EventSource(update_url);
  evtSource.onmessage = function (e) {
    var data = JSON.parse(e.data)
    for (const name in data) {
      if (!(name in evtSources)) {
        var progress_url = utils.url_path_join(jhdata.base_url, "api/users", user, "servers", name, "progress");
        var progress_bar = $("#" + name + "-progress-bar");
        var progress_log = $("#" + name + "-progress-log");

        evtSources[name] = new EventSource(progress_url);
        evtSources[name]["name"] = name;
        evtSources[name]["progress_bar"] = progress_bar;
        evtSources[name]["progress_log"] = progress_log;
        evtSources[name].onmessage = function (e) {
          onEvtMessage(e, evtSources[name], evtSources[name]["progress_bar"], evtSources[name]["progress_log"]);
        }

        progress_bar.removeClass("bg-success bg-danger");
        progress_bar.css("width", "0%");
        progress_log.html("");

        // Update buttons to reflect pending state
        var row = $('tr[data-server-name="' + name + '"]').first();
        enableRow(row, true);
      }
    }
  }


  /*
  Callbacks to handle button clicks
  */

  function getRow(button) {
    return button.parents("tr");
  }

  function getCollapse(row) {
    var server_name = row.data("server-name");
    var collapse = row.siblings(`.collapse-tr[data-server-name=${server_name}]`);
    return collapse;
  }

  function disableRow(tr) {
    // Disable buttons
    tr.find("button").addClass("disabled");
  }

  function enableRow(tr, running) {
    var na = tr.find(".na-status").text()
    tr.find("button").removeClass("disabled");

    if (running) {
      tr.find(".na").addClass("d-none")
      tr.find(".start").addClass("d-none");
      tr.find(".delete").addClass("d-none");
      tr.find(".open").removeClass("d-none");
      tr.find(".stop").removeClass("d-none");
      // Disable until fitting event received from EventSource
      tr.find(".open").addClass("disabled");
      tr.find(".stop").addClass("disabled");
    } else {
      if (na == "1") {
        tr.find(".na").removeClass("d-none")
        tr.find(".start").addClass("d-none");
      } else {
        tr.find(".na").addClass("d-none")
        tr.find(".start").removeClass("d-none");
        tr.find(".delete").removeClass("d-none");
        tr.find(".open").addClass("d-none");
        tr.find(".stop").addClass("d-none");
      }
    }
  }

  function cancelServer(event) {
    event.preventDefault();
    event.stopPropagation();

    var tr = getRow($(this));
    var server_name = tr.data("server-name");
    disableRow(tr);

    api.cancel_named_server(user, server_name, {
      success: function () {
        enableRow(tr, false);
        // Only reset progress bar if stopping a running server
        // If cancelling, we want to keep the progress indicator
        var progress_bar = tr.find(".progress-bar");
        if (progress_bar.hasClass("bg-success")) {
          progress_bar.removeClass("bg-sucess");
          progress_bar.width(0);
          progress_bar.html('');
        }
      },
    });
  }

  function stopServer(event) {
    event.preventDefault();
    event.stopPropagation();

    var tr = getRow($(this));
    var server_name = tr.data("server-name");
    disableRow(tr);

    api.stop_named_server(user, server_name, {
      success: function () {
        enableRow(tr, false);
      },
    });
  }

  function deleteServer(event) {
    event.preventDefault();
    event.stopPropagation();

    var collapse_row = getRow($(this));
    disableRow(collapse_row);

    var server_name = collapse_row.data("server-name");
    var tr = collapse_row.siblings(`[data-server-name=${server_name}]`);

    api.delete_named_server(user, server_name, {
      success: function () {
        tr.each(function () {
          $(this).remove();
        })
        collapse_row.remove();
      },
    });
  }

  function startServer(event) {
    event.preventDefault();
    event.stopPropagation();

    // askForNotificationPermission();

    var tr = getRow($(this));
    var collapse = getCollapse(tr);
    disableRow(tr);

    var name = tr.data("server-name");
    var url = utils.url_path_join(base_url, "spawn", user, name);
    url = createUrlAndUpdateTr(url, collapse, tr);
    $(this).attr("href", url);

    var options = createDataDict(collapse);

    // Validate the form and start spawn only after validation
    try {
      $(`form[id*=${name}]`).submit();
      var progress_bar = $("#" + name + "-progress-bar");
      // Get the card instead of the parent div for the log
      var progress_log = $("#" + name + "-progress-log");
      progress_bar.removeClass("bg-success bg-danger");
      progress_bar.css("width", "0%");
      progress_log.html("");
      var newTab = window.open("about:blank");

      api.start_named_server(user, name, {
        data: JSON.stringify(options),
        success: function () {
          newTab.location.href = url;
          // hook up event-stream for progress
          var progress_url = utils.url_path_join(jhdata.base_url, "api/users", jhdata.user, "servers", name, "progress");
          if (!(name in evtSources)) {
            evtSources[name] = new EventSource(progress_url);
            evtSources[name]["name"] = name;
            evtSources[name]["progress_bar"] = progress_bar;
            evtSources[name]["progress_log"] = progress_log;
            evtSources[name].onmessage = function (e) {
              onEvtMessage(e, evtSources[name], evtSources[name]["progress_bar"], evtSources[name]["progress_log"]);
            }
          }

        },
        error: function (xhr, textStatus, errorThrown) {
          progress_bar.css("width", "100%");
          progress_bar.attr("aria-valuenow", 100);
          progress_bar.addClass("bg-danger");
          progress_log.append($("<div>").html(
            `Could not request spawn. Error: ${xhr.status} ${errorThrown}`)
          )
          enableRow(tr, false);
        }
      });
      enableRow(tr, true);
    } catch (e) {
      enableRow(tr, false);
    }
  }

  function startNewServer() {
    $(this).attr("disabled", true);
    var button = $(this);
    var spinner = $(this).children().first();
    var alert = $(this).siblings(".alert");
    spinner.removeClass("d-none");

    // askForNotificationPermission();

    // Automatically set name if none was specified
    var name = $("#new_jupyterlab-name-input").val();
    if (name == "") {
      var c = 1;
      do {
        var servername = "jupyterlab_" + c;
        c += 1;
      } while ($(`[data-server-name=${servername}]`).length > 0)
      name = servername;
    }

    var url = utils.url_path_join(base_url, "spawn", user, name);
    url = createUrlAndUpdateTr(url, $("#new_jupyterlab-configuration"));
    $(this).attr("href", url);

    var search_element = $("#new_jupyterlab-dialog").find(".modal-content");
    var options = createDataDict(search_element);
    // console.log(url);

    try {
      $("form[id*=new_jupyterlab]").submit();
      var newTab = window.open("about:blank");
      alert.children("span").text(`Waiting for ${name} to start...`);
      alert.removeClass("alert-danger").addClass("show alert-dark");
      api.start_named_server(user, name, {
        data: JSON.stringify(options),
        success: function () {
          newTab.location.href = url;
          var myModal = $("#new_jupyterlab-dialog");
          var modal = bootstrap.Modal.getInstance(myModal);
          modal.hide();
          button.removeAttr("disabled");
          spinner.addClass("d-none");
          alert.removeClass("show");
          location.reload();
        },
        error: function (xhr, textStatus, errorThrown) {
          spinner.addClass("d-none");
          button.removeAttr("disabled");
          alert.removeClass("alert-dark").addClass("show alert-danger");
          alert.children("span").text(`Could not start ${name}. Error: ${xhr.status} ${errorThrown}`);
        }
      });
    } catch (e) {
      $(this).removeAttr("disabled");
    }
  }

  function openServer(event) {
    event.preventDefault();
    event.stopPropagation();

    var url = $(this).data("server-url");
    window.open(url, "_blank");
  }

  $(".stop").click(cancelServer);
  // $(".stop").click(stopServer);
  $(".delete").click(deleteServer);
  $(".start").click(startServer);
  $("#new_jupyterlab-start-btn").click(startNewServer);
  $(".open").click(openServer);


  /*
  Validate form before starting a new lab
  */
  $("form").submit(function (event) {
    event.preventDefault();
    event.stopPropagation();

    if (!$(this)[0].checkValidity()) {
      $(this).addClass('was-validated');
      // Show the tab where the error was thrown
      var tab_id = $(this).attr("id").replace("-form", "-tab");
      var tab = new bootstrap.Tab($("#" + tab_id));
      tab.show();
      // Open the collapse if it was hidden
      var collapse = $(this).parents(".collapse");
      var first_td = $(this).parents("tr").prev().children().first();
      var icon = first_td.children().first();
      var hidden = collapse.css("display") == "none" ? true : false;
      if (hidden) {
        icon.removeClass("collapsed");
        new bootstrap.Collapse(collapse);
      }
      throw {
        name: "FormValidationError",
        toString: function () {
          return this.name;
        }
      };
    } else {
      $(this).removeClass('was-validated');
    }
  });


  /*
  Save and revert changes to spawner
  */
  function saveChanges() {
    var collapse = $(this).parents(".collapse");
    var tr = $(this).parents("tr").prev();
    var alert = $(this).siblings(".alert");

    var name = $(this).attr("id").split('-')[0];
    var server_name = collapse.find("input[id*=name]").val();
    var options = createDataDict(collapse);

    api.update_named_server(user, server_name, {
      data: JSON.stringify(options),
      success: function () {
        // Update table data entries
        updateTr(collapse, tr);
        // Update user options
        user_options[name] = options;
        // Update alert message
        alert.children("span").text(`Successfully updated ${server_name}.`);
        alert.removeClass("alert-danger pe-none");
        alert.addClass("alert-success show");
        // Disable edit buttons again
        $("#" + name + "-save-btn").attr("disabled", true);
        $("#" + name + "-reset-btn").attr("disabled", true);
      },
      error: function (xhr, textStatus, errorThrown) {
        alert.children("span").text(`Could not update ${server_name}. Error: ${xhr.status} ${errorThrown}`);
        alert.removeClass("alert-success pe-none");
        alert.addClass("alert-danger show");
      }
    });
  }

  function revertChanges() {
    var collapse = $(this).parents(".collapse");
    var tr = $(this).parents("tr").prev();
    var alert = $(this).siblings(".alert");

    var name = $(this).attr("id").split('-')[0];
    var options = user_options[name];

    api.update_named_server(user, name, {
      data: JSON.stringify(options),
      success: function () {
        // setValues and removeWarning from new_home.html
        setValues(name, user_options[name]);
        removeWarnings(name); // Remove all warning badges
        // Update table data entries
        updateTr(collapse, tr)
        // Show first tab after resetting values
        var trigger = $("#" + name + "-service-tab");
        var tab = new bootstrap.Tab(trigger);
        tab.show();
        // Update alert message
        alert.children("span").text(`Successfully reverted settings back for ${name}.`);
        alert.removeClass("alert-danger pe-none");
        alert.addClass("alert-success show");
        // Disable edit buttons again
        $("#" + name + "-save-btn").attr("disabled", true);
        $("#" + name + "-reset-btn").attr("disabled", true);
      },
      error: function (xhr, textStatus, errorThrown) {
        alert.children("span").text(`Could not update ${name}. Error: ${xhr.status} ${errorThrown}`);
        alert.removeClass("alert-success pe-none");
        alert.addClass("alert-danger show");
      }
    });
  }

  $(".save").click(saveChanges);
  $(".reset").click(revertChanges);
  
  // Check if there are changes and thus if the save and revert buttons should be enabled
  $("select, input").change(function () {
    var that = $(this);
    var id = $(this).attr("id").split('-')[0];
    var option = $(this).attr("id").split('-')[1];
    var options = user_options[id];

    if (options) {
      switch (option) {
        case "type":
          var option_key = "options_input";
          break;
        case "nodes":
        case "runtime":
          var option_key = "resource_" + option[0].toUpperCase() + option.substring(1);
          break;
        case "gpus":
          var option_key = "resource_GPUS";
          break;
        default:
          var option_key = option + "_input";
      }

      var old_value = options[option_key];
      if (that.val() != old_value) {
        $("#" + id + "-save-btn").removeAttr("disabled");
        $("#" + id + "-reset-btn").removeAttr("disabled");
      }
    }
  })


  /*
  Util functions
  */
  function createUrlAndUpdateTr(url, collapse, tr) {
    url += "?vo_active_input=" + $("#vo-form input[type='radio']:checked").val();
    url += "&service_input=" + "JupyterLab";

    function addParameter(param, option_name = null, input = false) {
      if (!option_name) var option_name = param + "_input";

      if (input) { // <input>
        var input = collapse.find(`input[id*=${param}]`);
        var parent_div = input.parents(".row").first();
        if (parent_div.css("display") == "none") {
          return;
        }
        var value = input.val();
        if (option_name == "resource_Runtime") {
          value = value * 60;
        }
      }
      else { // <select>
        var select = collapse.find(`select[id*=${param}]`);
        var value = select.val();

        // For new jupterlabs, no tr exists that can be updated
        if (tr) {
          switch (param) {
            case "system":
              var td = tr.find(".system-td");
              td.text(value);
              break;
            case "partition":
              var td = tr.find(".partition-td");
              td.text(value);
              break;
            case "project":
              var td = tr.find(".project-td");
              td.text(value);
              break;
          }
        }
      }

      if (value != null && value != "") url += "&" + option_name + "=" + value;
    }

    addParameter("type", "options_input");
    addParameter("system");
    addParameter("account");
    addParameter("project");
    addParameter("partition");
    addParameter("reservation");
    addParameter("nodes", "resource_Nodes", true);
    addParameter("gpus", "resource_GPUS", true);
    addParameter("runtime", "resource_Runtime", true);

    return url;
  }

  function createDataDict(collapse) {
    var user_options = {}
    user_options["vo_active_input"] = $("#vo-form input[type='radio']:checked").val();
    user_options["service_input"] = "JupyterLab";

    function addParameter(param, option_name = null, input = false) {
      if (!option_name) var option_name = param + "_input";

      if (input) { // <input>
        var input = collapse.find(`input[id*=${param}]`);
        var parent_div = input.parents(".row").first();
        if (parent_div.css("display") == "none") {
          return;
        }
        var value = input.val();
        if (option_name == "resource_Runtime") {
          value = value * 60;
        }
      }
      else { // <select>
        var select = collapse.find(`select[id*=${param}]`);
        var value = select.val();
      }

      if (value != null) user_options[option_name] = value;
    }

    addParameter("type", "options_input");
    addParameter("system");
    addParameter("account");
    addParameter("project");
    addParameter("partition");
    addParameter("reservation");
    addParameter("nodes", "resource_Nodes", true);
    addParameter("gpus", "resource_GPUS", true);
    addParameter("runtime", "resource_Runtime", true);

    return user_options;
  }

  function updateTr(collapse, tr) {
    var system_td = tr.find(".system-td");
    system_td.text(collapse.find("select[id*=system]").val());
    var partition_td = tr.find(".partition-td");
    partition_td.text(collapse.find("select[id*=partition]").val());
    var project_td = tr.find(".project-td");
    project_td.text(collapse.find("select[id*=project]").val());
  }

  /* Moved to home.html */
  // Handle EventSource message
  // function onEvtMessage(event, evtSource, progress_bar, progress_log) {
  // }
});