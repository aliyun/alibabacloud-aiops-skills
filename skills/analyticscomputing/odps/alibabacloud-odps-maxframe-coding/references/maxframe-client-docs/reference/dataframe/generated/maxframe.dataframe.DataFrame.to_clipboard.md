# maxframe.dataframe.DataFrame.to_clipboard

#### DataFrame.to_clipboard(, excel=True, sep=None, batch_size=10000, session=None, \*\*kwargs)

Copy object to the system clipboard.

Write a text representation of object to the system clipboard.
This can be pasted into Excel, for example.

* **Parameters:**
  * **excel** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – 

    Produce output in a csv format for easy pasting into excel.
    - True, use the provided separator for csv pasting.
    - False, write a string representation of the object to the clipboard.
  * **sep** (str, default `'      '`) – Field delimiter.
  * **\*\*kwargs** – These parameters will be passed to DataFrame.to_csv.

#### SEE ALSO
[`DataFrame.to_csv`](maxframe.dataframe.DataFrame.to_csv.md#maxframe.dataframe.DataFrame.to_csv)
: Write a DataFrame to a comma-separated values (csv) file.

[`read_clipboard`](maxframe.dataframe.read_clipboard.md#maxframe.dataframe.read_clipboard)
: Read text from clipboard and pass to read_csv.

### Notes

Requirements for your platform.

> - Linux : xclip, or xsel (with PyQt4 modules)
> - Windows : none
> - macOS : none

This method uses the processes developed for the package pyperclip. A
solution to render any output string format is given in the examples.

### Examples

Copy the contents of a DataFrame to the clipboard.

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([[1, 2, 3], [4, 5, 6]], columns=['A', 'B', 'C'])
```

```pycon
>>> df.to_clipboard(sep=',')
... # Wrote the following to the system clipboard:
... # ,A,B,C
... # 0,1,2,3
... # 1,4,5,6
```

We can omit the index by passing the keyword index and setting
it to false.

```pycon
>>> df.to_clipboard(sep=',', index=False)
... # Wrote the following to the system clipboard:
... # A,B,C
... # 1,2,3
... # 4,5,6
```
