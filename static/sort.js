function sort(column) {

    var field, display_type, tr, all_columns, sorted_columns, x, y, tmp, a, dir, th_classes, th;

    field = "." + column.className.split(" ")[0]
    display_type = column.className.split(" ")[1]
    tr = document.querySelectorAll("tr.not-hidden");

    // Set direction of sort
    th_classes = Array.from(column.classList);
    if (th_classes.includes("asc"))
    {
        dir = "desc";
    }
    else
    {
        dir = "asc";
    }

    const nums = [".mass", ".pieces"]

    // Resets previous sorts
    all_columns = document.querySelectorAll("td, th, input")

    for (a = 0; a < all_columns.length; a++)
    {
        all_columns[a].classList.remove("text-primary");
    }

    th = document.querySelectorAll("th.text, th.edit");
    for (a = 0; a < th.length; a++)
    {
        th[a].classList.remove("asc");
        th[a].classList.remove("desc");
    }

    // Sort by Bubble Sort
    for (var i = 0; i < (tr.length - 1); i++)
    {
        for(var j = 0; j < (tr.length - i - 1); j++)
        {
            // Get data of cell
            if (display_type == "edit")
            {
                x = tr[j].querySelector(field).value.toUpperCase();
                y = tr[j + 1].querySelector(field).value.toUpperCase();
            }
            else
            {
                x = tr[j].querySelector(field).innerText.toUpperCase();
                y = tr[j + 1].querySelector(field).innerText.toUpperCase();
            }

            // Compare based on number or string
            if (nums.includes(field))
            {
                if (dir == "asc")
                {
                    if (Number(x) > Number(y))
                    {
                        console.log(tr[j].outerHTML);
                        tmp = tr[j].innerHTML;
                        tr[j].innerHTML = tr[j + 1].innerHTML;
                        tr[j + 1].innerHTML = tmp;
                    }
                }
                else
                {
                    if (Number(x) < Number(y))
                    {
                        tmp = tr[j].innerHTML;
                        tr[j].innerHTML = tr[j + 1].innerHTML;
                        tr[j + 1].innerHTML = tmp;
                    }
                }
            }
            else
            {
                if (dir == "asc")
                {
                    if (x.localeCompare(y) > 0)
                    {
                        tmp = tr[j].innerHTML;
                        tr[j].innerHTML = tr[j + 1].innerHTML;
                        tr[j + 1].innerHTML = tmp;
                    }
                }
                else
                {
                    if (x.localeCompare(y) < 0)
                    {
                        tmp = tr[j].innerHTML;
                        tr[j].innerHTML = tr[j + 1].innerHTML;
                        tr[j + 1].innerHTML = tmp;
                    }
                }

            }

        }
    }

    // Changes color of text to highlight sorted column
    sorted_columns = document.querySelectorAll(field)

    for (var b = 0; b < sorted_columns.length; b++)
    {
        sorted_columns[b].classList.add("text-primary");
    }

    // Save direction of sort
    column.classList.add(dir)
}