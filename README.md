# Cahaya Walet Jaya Management System
#### Video Demo:

#### Description:
A simple management system for PT. Cahaya Walet Jaya (where my father works) implemented as a web app using Flask. As of now, the management system only handles purchases, and is akin to a glorified Microsoft Excel or Google Sheets. Its main functions are the storing of purchase data, displaying them with the option of filtering and/or sorting them, editing of previous entries and summarising the data based on certain categories.

It can and will be upgraded sometime in the future to include other sections, such as *sorting*, *finances*, etc. and more features, although a different framework may be used depending on the circumstance.

**Important Notice:** This web app is meant to be used primarily on **Desktop only**. Because of the nature of the tables (i.e., the large number of fields being displayed), the web app will not display properly on mobile. Only the *Input Purchase Data* section will display properly on mobile devices.
st

## ! Disclaimer:
This is an unofficial web app for education purposes; I am not directly affliated to nor does this web app represent PT. Cahaya Walet Jaya. I am only using it as an example and frame such my database may reflect those used in actual industry. Any and all data used are random data used as filler for testing purposes and are not actual data from PT. Cahaya Walet Jaya.


## Overview:
There are 3 levels of access for the web app, each with a differing number of functions.

#### 1. General Access (No Login Required):
* / : View purchase data in the form of a table with the ability to filter and/or sort them.
* /purchase_reports : Same with index, with the difference being only one specific filter is available above the table, making the table somewhat cleaner to look at.
* /purchase_summary : View a summary of the total mass of the birds' nests separated by color grade, shape and feather amount.
* /login : Allows admins to log in.

#### 2. Admin Access (Login Required):
All of the functions in *General Access*, with the addition of the following:
* / : "Edit" button is visible which redirects admins to /edit_purchase.
* /edit_purchase : Allows admins to edit entries by changing the value of their respective cells as how you would in Microsoft Excel or Google Sheets. Edits are only saved once the "confirm" button is clicked, and only edits for that row are saved; any changes in other rows will be lost. Time of last edit and the admin responsible is also visible. Admins can also delete entire rows into the "recycle bin".
* /input_purchase : Allows admins to store a new entry into the database.
* /restore_purchase : Serves as a "recycle bin" and allows admins to restore entries previously deleted.
* /admins : View the list of admins, which includes their *ID*, *Name*, *Username* and *Email*.
* /logout : Logs admin out
* /login : Allows admins to log in, and "Forgot Password?" redirects to /reset_password
* /reset_password : Sends an email with a "link" to /set_password that allows admins to set their password.
* /set_password : Allows admins to set their password and activate their account.

#### 3. Master Access (Master Account Only):
All of the functions in *Admin Access*, with the addition of the following:
* /restore_purchase : Option to delete an entry permanently is available.
* /admins : "Register New Admin" button is visible which redirects to /register_admin. Option to delete an admin is available.
* /register_admin : Registers a new admin, sending the admin an email with a "link" to /set_password to activate their account and set their password.


## Database Context & Explanation:
My father works in the bird's nest industry (the edible kind that can be found in Eastern cuisine & medicine) and the database fields are created to somewhat reflect it. There are 3 tables in total: *purchases*, *admins*, and *deleted_purchases*.

The *purchases* table contains the following fields:
* date : Date of shipment arrival
* supplier : Name of supplier
* supplier_code : Unique ID of supplier
* purchase_code : ID of the purchase batch, similar to that on a receipt
* shape : Shape of the bird's nest, limited to bowl, triangle, oval, and fragments.
* feather : Amount of feathers present, limited to clean, light, medium, and heavy.
* color : Colour grade of the bird's nest, limited to A, B, C, and D
* mass : Total mass of batch
* pieces : Number of individual bird's nests in the batch
* admin_id : ID of admin responsible for entry changes
* edit_time : Time of entry edit

For simplicity, you can just think of the *shape*, *feathers*, and *color* fields as qualitative categories of the bird's nest.

The *admins* table contains the *admin_id*, *name*, *username*, *email*, *password_hash*, and *account_hash* (a unique and random string affiliated to each admin account).

The *deleted_purchases* table has the exact same schema as the *purchases* table, and serves as a recycle bin in case of accidental deletion and the recovery of individual entries.


## Significant Design Choices:
My web app makes heavy use of templating to generate its pages, and only a few aspects are hard coded into the HTML files.

#### The purchase_columns List
For aspects of the web app related to the purchase data, from the input form to the display tables, I've opted to make use of a list containing dictionaries that describe each field, a snippet of which is shown below.
```
purchase_columns = [
    {"name": "date", "label": "Date", "type": "date"},
    {"name": "supplier", "label": "Supplier", "type": "text"},
    ...
    ]
```
As such, to add a new column I simply need to add a dictionary for it into the purchase_columns list and alter the schema of the database file. An additional benefit is that it makes my HTML templates relatively simple, and for pages with similar displays like the *index*, *edit_purchase*, *purchase_reports*, *restore_purchase*, only a few aspects are changed like the amount of filters, and whether the data is directly used in the *td* element or used as the value of an *input* element for the editable display.

Although I am relying on the browser provided validation for the front-end, I've made a validate function for the back-end which also makes use of the above list as well as a few others like the *uppercase* and *lowercase* lists to normalise the input. The function validates based on the same dictionary keys used for front-end validation like *type*, *min* and *step* for numbers, and *options* for select type inputs.

This technique also makes it relatively easy to scale the web app to include other departments; simply set up a new list, while the HTML templates can remain mostly unchanged. An example of which would be the input form HTML template, of which only the Heading and Action of the form needs to be updated.

#### purchase_reports
The *purchase_reports* are almost the exact same with the *index*, the only exception being the *purchase_reports* makes use of only 1 filter. To add a new filter, it just needs to be added into the *label* list below and add the link to the dropdown nav of the *layout*.
```
    labels = {
        "supplier": "Supplier",
        "purchase_code": "Purchase Code",
        "shape": "Shape",
    }
```

#### purchase_summary
The *purchase_summary* is the one I'm most proud of. It makes use of essentially a 3-dimensional dictionary which is accessed like the following and filled using 3 nested loops.
```
summary[color_key][shape][feather]
```
The code of the route seems a bit long because I had to construct SQL commands for the *grand total*, *total per feather*,*total per shape* and *sum per feather per shape* which are the individual cells. The 4 had to be duplicated to take into account whether only one color is considered or all of them, bringing the total to 8 SQL commands which otherwise would've been 125 distinct SQL commands. To reduce the load time, I've also created an index in the database for these 3 columns which were queried.

And because all of the data is stored in one dictionary, the HTML template to display the tables is very simple by use of loops.

#### delete_purchase and restore_purchase
Since it is easy to accidentally delete an entry in the purchase table, I've implemented a recycle bin as temporary storage. When an entry is deleted, it is copied to the *deleted_purchases* table before being removed from the *purchases* table. Once in the *deleted_purchases* table, only the master account has the ability to permanently delete the entry while any other admin can restore it.

#### Sort
My sorting function makes use of bubble sort, since it is easy to implement as quick since the dataset I'm using only consists of a few rows. To allow for bidirectional sorting, the *asc* and *desc* classes are used to indicate the previous sorting's direction. When upgrading the web app to accommodate for larger datasets in the future, I will be relying on external libraries rather than my own sorting function.

#### Filter
I got the basic concept for the filter from [W3 Schools](https://www.w3schools.com/howto/howto_js_filter_table.asp), from which I've adapted into my web app. The *input* elements which are used as the filters themselves makes use of 2 classes, *filter* and *text*/*edit*. The *filter* class is used to target the filter inputs, while the *text*/*edit* class is used to indicate whether its corresponding columns makes use of the *td* element directly or an *input* element since one would require *.innerText* while the other *.value* to get the cell data.

To make the filters inclusive of each other, the display is reset each time and rows that don't match any of the filters are hidden.

The total count is updated only after the filter is applied rather than during it to make the code much cleaner and readable.

#### Admins
When registering a new admin, the account is set up with the *name*, *username* and *email* as filled by the Master Account and two random hashes are generated for the password hash and account hash. This account hash is included in the email sent to the registered admin so that they can set their own passwords. The account hash also enables the admins to reset their password in case they've forgotten it.

The account hash is generated anew each time the password is set so that the link is one time use.

For security when setting the password, all admin fields are cross-checked with those in the *admins* table so that a person cannot change the password of another account without having the link/account hash of said account.