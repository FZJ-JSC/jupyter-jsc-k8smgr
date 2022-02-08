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

  $(document).ready(function () {
    // Set lab name
    var pathname = window.location.pathname;
    var name = pathname.split('/').pop();
    $('input[type=name]').val(name);
  })

  /*
  Start new lab
  */
  function startNewServer() {
    // $(this).attr("disabled", true);

    var name = $("#new_jupyterlab-name-input").val();
    var url = utils.url_path_join(base_url, "spawn", user, name);
    url = createUrl(url);
    $(this).attr("href", url);

    var search_element = $("#new_jupyterlab-dialog").find(".modal-content");
    var options = createDataDict(search_element);
    console.log(url, options);

    try {
      $("form[id*=new_jupyterlab]").submit();
      // var newTab = window.open("about:blank");
      api.start_named_server(user, name, {
        data: JSON.stringify(options),
        success: function () {
          // newTab.location.href = url;
          $(this).removeAttr("disabled");
          window.location = url;
        },
        error: function (xhr, textStatus, errorThrown) {
          $(this).removeAttr("disabled");
          // Display error somewhere
        }
      });
    } catch (e) {
      $(this).removeAttr("disabled");
    }
  }

  $("#new_jupyterlab-start-btn").click(startNewServer);


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
  Warning icons and borders
  */

  // Check if warning badge whould be shown in tab
  $("[id*=tab-warning]").on("change", function () {
    var tab_warning = $(this);
    var tab = tab_warning.parent();
    var tab_content = $(tab.data("bsTarget"));
    var badges = tab_content.find(".badge");
    var should_show = false;

    badges.each(function () {
      if ($(this).css("display") != "none") should_show = true;
    })

    if (should_show && !tab.hasClass("disabled")) {
      tab_warning.show();
    } else {
      tab_warning.hide();
    }
  });

  // Remove warning icons when clicking on inputs
  function onFocus(select, tab_name, setting = "select") {
    var id = select.attr("id").split('-')[0];
    var warning_id = select.attr("id").replace("-" + setting, "-warning");
    select.removeClass("border-warning");
    $("#" + warning_id).hide();
    $("#" + id + "-" + tab_name + "-tab-warning")[0].dispatchEvent(new Event("change"));
  }

  $("div[id*=service] input").on("input", function () {
    onFocus($(this), "service", setting = "input");
  });

  $("div[id*=service] select").focus(function () {
    onFocus($(this), "service");
  });

  $("div[id*=options] select").focus(function () {
    onFocus($(this), "options");
  });

  $("div[id*=resources] input").focus(function () {
    onFocus($(this), "resources", setting = "input");
  });

  $("div[id*=reservation] select").focus(function () {
    onFocus($(this), "reservation");
  });


  /*
  Util functions
  */
  function createUrl(url) {
    url += "?vo_active_input=" + $("#vo-form input[type='radio']:checked").val();
    url += "&service_input=" + "JupyterLab";

    function addParameter(param, option_name = null, input = false) {
      if (!option_name) var option_name = param + "_input";

      if (input) { // <input>
        var input = $(`input[id*=${param}]`);
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
        var select = $(`select[id*=${param}]`);
        var value = select.val();
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

  function createDataDict() {
    var user_options = {}
    user_options["vo_active_input"] = $("#vo-form input[type='radio']:checked").val();
    user_options["service_input"] = "JupyterLab";

    function addParameter(param, option_name = null, input = false) {
      if (!option_name) var option_name = param + "_input";

      if (input) { // <input>
        var input = $(`input[id*=${param}]`);
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
        var select = $(`select[id*=${param}]`);
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
})