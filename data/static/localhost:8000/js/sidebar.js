$(window).on('load', function () {
  /* Set correct paddings and margins */
  spaceHeader();
  $(window).on('resize orientationchange', spaceHeader)
})

$(document).ready(function () {
    /* Set active nav entry in sidebar */
    var pathname = window.location.pathname;
    $("#sidebar .nav-link").removeClass("active");
    if (pathname.includes("/hub/home") || pathname.includes("/hub/spawn-pending")) {
      setActive("JupyterLab");
    }
    else if (pathname.includes("/hub/admin")) {
      var hash = window.location.href;
      if (hash.includes("#logging")) {
        setActive("Logging");
      }
      else if (hash.includes("#users")) {
        setActive("User Labs");
      }
    }
})

// $(".navbar-toggler").on("click", function () {
//   if ($(this).hasClass("collapsed")) {
//     $("header").addClass("shadow");
//   } else {
//     $("header").removeClass("shadow");
//   }
// })

function spaceHeader() {
  var header = $("header");
  var first_nav = header.children().first();
  var second_nav = header.children().last();
  if (second_nav.css("display") != "none") {
    second_nav.css("margin-top", first_nav.height());
    // $("main").css("margin-top", header.height());
  }
  else {
    // $("main").css("margin-top", first_nav.height());
  }
  $(".sidebar").css("padding-top", first_nav.height() + second_nav.height());
}

function setActive(listItem) {
  var navLink = $(`#sidebar .nav-link:contains(${listItem})`);
  var navLinkDiv = navLink.parent();
  navLink.addClass("active");
  navLinkDiv.addClass("active");
  navLinkDiv.append('<div class="arrow-left ms-auto"></div>');
}

function removeActive(listItem) {
  var navLink = $(`#sidebar .nav-link:contains(${listItem})`);
  var navLinkDiv = navLink.parent();
  navLink.removeClass("active");
  navLinkDiv.removeClass("active");
  navLinkDiv.children().last().remove();
}