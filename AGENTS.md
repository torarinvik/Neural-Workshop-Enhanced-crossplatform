# Repository instructions

- Keep every source file at or below 600 lines. Split larger files by responsibility.
- Organize code into subfolder whenever a folder contains more than 20 files
- Regularly clean up repo to make it look as professional as possible
- Make sure documentation is up to date at all time
- Do not commit temporary scripts or temporary documentation.

* Use expression based style that can be enforced by the compiler such as loop expressions and block expressions
* Use modules including submodules with good public/private hygiene

* Make sure functions are reasonably sized and no larger than necessary
* Keep total amount of struct fields less than 20, split up and prefer composition with more is needed
* Avoid abbreviations, use explicit names eg. instead of mat_expr use matrix_expression.
* Prefer zero overhead threading of mutable datatypes instead of in place mutation of mutable references
  * def foo(an_array: mutable darray[u8]) ->  darray[u8]

* Use block expressions to encapsulate data
