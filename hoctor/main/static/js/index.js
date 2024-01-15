$(".launch-btn").click(function() {
    $(".second-page").css({
        "clip-path": "circle(100%)",
    })
});

// document.addEventListener("mousemove", parallax);
// function parallax(e) {
//     console.log("eunning")
//   document.querySelectorAll(".el").forEach((element) => {
//     const speed = element.getAttribute("data-speed");
//     const x = (window.innerWidth - e.pageX * speed) / 200;
//     const y = (window.innerHeight - e.pageY * speed) / 200;

//     element.style.transform = "translate(" + x + "px," + y + "px)";
//   });
// }