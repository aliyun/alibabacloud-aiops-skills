# maxframe.dataframe.DataFrame.reorder_levels

#### DataFrame.reorder_levels(order, axis=0)

Rearrange index levels using input order. May not drop or duplicate levels.

* **Parameters:**
  * **order** ([*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*int*](https://docs.python.org/3/library/functions.html#int) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – List representing new level order. Reference level by number
    (position) or by key (label).
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – Where to reorder levels.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> data = {
...     "class": ["Mammals", "Mammals", "Reptiles"],
...     "diet": ["Omnivore", "Carnivore", "Carnivore"],
...     "species": ["Humans", "Dogs", "Snakes"],
... }
>>> df = md.DataFrame(data, columns=["class", "diet", "species"])
>>> df = df.set_index(["class", "diet"])
>>> df.execute()
                                  species
class      diet
Mammals    Omnivore                Humans
           Carnivore                 Dogs
Reptiles   Carnivore               Snakes
```

Let’s reorder the levels of the index:

```pycon
>>> df.reorder_levels(["diet", "class"]).execute()
                                  species
diet      class
Omnivore  Mammals                  Humans
Carnivore Mammals                    Dogs
          Reptiles                 Snakes
```
