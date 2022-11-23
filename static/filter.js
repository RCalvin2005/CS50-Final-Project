function filter(total_type) {

    // Base concept source: https://www.w3schools.com/howto/howto_js_filter_table.asp

    // Declare variables
    var filters, filter, field, tr, td, sum_mass, sum_pieces, match;

    filters = document.querySelectorAll(".filter");
    tr = document.querySelectorAll("tr.align-middle");

    // Resets display
    for (var a = 0; a < tr.length; a++)
    {
        tr[a].style.display = "";
        tr[a].classList.add("not-hidden");
    }

    // Loop through all the filters
    for (var i = 0; i < filters.length; i ++)
    {

        filter = filters[i].value.toUpperCase();

        if (filter)
        {
            field = "." + filters[i].name

            if (filters[i].className.indexOf("edit") > -1)
            {
                display_type = "edit"
            }
            else
            {
                display_type = "text"
            }

            // Loop through table rows, hiding rows that don't match search query
            for (var j = 0; j < tr.length; j++)
            {

                // Check if row is not hidden
                if (tr[j].style.display != "none")
                {

                    td = tr[j].querySelector(field);

                    if (display_type == "edit")
                    {
                        match = td.value.toUpperCase().indexOf(filter) > -1
                    }
                    else
                    {
                        match = td.innerText.toUpperCase().indexOf(filter) > -1
                    }

                    if (!match)
                    {
                        // Hide row if not match
                        tr[j].style.display = "none";
                        tr[j].classList.remove("not-hidden")
                    }
                }
            }
        }
    }

    // Calculate total for visible rows
    if (total_type)
    {
        sum_mass = 0;
        sum_pieces = 0;
        for (var b = 0; b < tr.length; b++)
        {
            if (tr[b].style.display == "")
            {
                if (total_type == "edit")
                {
                    sum_mass += parseFloat(tr[b].querySelector(".mass").value);
                    sum_pieces += parseInt(tr[b].querySelector(".pieces").value);
                }
                else
                {
                    sum_mass += parseFloat(tr[b].querySelector(".mass").innerText);
                    sum_pieces += parseInt(tr[b].querySelector(".pieces").innerText);
                }

            }
        }
        document.querySelector("#sum_mass").innerText = sum_mass.toFixed(2);
        document.querySelector("#sum_pieces").innerText = sum_pieces;
    }

}