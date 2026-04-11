(function () {
    function toggleInterviewFields() {
        const typeField = document.getElementById("id_interview_type");
        const meetingWrap = document.querySelector(".js-meeting-link-wrap");
        const locationWrap = document.querySelector(".js-location-wrap");
        const meetingInput = document.getElementById("id_meeting_link");
        const locationInput = document.getElementById("id_location");
        if (!typeField || !meetingWrap || !locationWrap) return;
        const value = typeField.value;
        const showMeeting = value === "video" || value === "phone";
        const showLocation = value === "onsite";
        meetingWrap.style.display = showMeeting ? "" : "none";
        locationWrap.style.display = showLocation ? "" : "none";
        if (!showMeeting && meetingInput) meetingInput.value = "";
        if (!showLocation && locationInput) locationInput.value = "";
    }
    document.addEventListener("DOMContentLoaded", function () {
        const typeField = document.getElementById("id_interview_type");
        if (typeField) {
            toggleInterviewFields();
            typeField.addEventListener("change", toggleInterviewFields);
        }
    });
})();
