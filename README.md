# LUIZA Notebooks: The Developer's Repository

The developer's repository is at [gitlab.com/michalgregor/ai_labs](https://gitlab.com/michalgregor/ai_labs). It is private.

Finished notebooks are published in a separate **public repository** at [github.com/michalgregor/luiza_notebooks](https://github.com/michalgregor/luiza_notebooks).

This readme file documents how to host and link data files required by notebooks, how to create links that open directly on Google Colab, how to create multi-lingual notebooks and export the different language versions, etc.

## Notebook Links That Open Directly on Google Colab

You can create links that open our GitHub-hosted notebooks directly in the Google Colab environment.

### Manually

This can either be done manually by creating URLs that follow format:
``https://colab.research.google.com/github/michalgregor/luiza_notebooks/blob/master/english/L1_python_intro/1_basic_syntax.ipynb``

### Using a Browser Extension

You can also use the [Open in Colab](https://chrome.google.com/webstore/detail/open-in-colab/iogfkhleblhcpcekbiedikdehleodpjo) Chrome extension. That way you just need to navigate to a notebook on GitHub, press a button and the link will be generated for you.

If you want to use a graphical badge when linking to a notebook, you can use the following piece of markdown:
```markdown
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/michalgregor/luiza_notebooks/blob/master/english/L1_python_intro/1_basic_syntax.ipynb)
```
or its HTML equivalent to get a badge like this:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/michalgregor/luiza_notebooks/blob/master/english/L1_python_intro/1_basic_syntax.ipynb)

## Linking to Data Files from Notebooks

1. Commit the data file first. If there are several related data files (e.g. train.csv, test.csv, info.txt), please either zip them or create a subfolder.
2. Navigate to the file in the repository at [github.com](https://github.com/michalgregor/luiza_notebooks).
3. Copy the file path relative to the ``data`` folder, i.e. use ``iris.csv`` if your file is at ``https://github.com/michalgregor/luiza_notebooks/blob/master/data/iris.csv``;
4. Use ``DATA_HOME.format("iris.csv")`` as the path to your file (see ``template_notebook.ipynb`` for examples).

Please, be careful when linking files from other sources; we want to make sure that they are always downloadable when users run the notebook, i.e. we do not want them to be refused access because of bandwidth quotas and such.

Be super careful whenever you decide to update files in the ``data/`` folder; keep in mind that other notebooks may rely upon them and they can break because of your changes.

## Setting a Notebook Up

Every notebook should be able to set up automatically: it should include code that installs the required packages, downloads the necessary data, etc.

Cells that contain such setup code should start with a header like    
```python
#@title -- Installation of Packages -- { display-mode: "form" }
```
so that the code is hidden when the notebook is opened on Google Colab.

## Writing and Exporting Notebooks

The developer's repository contains a [template notebook](https://gitlab.com/michalgregor/ai_labs/-/blob/master/template_notebook.ipynb), which illustrates some of the basic structure that notebooks should follow.

Once a set of notebooks is written, it can be exported using the ``export_notebooks.py`` script. This takes care of embedding images so that they display on Google Colab and of generating different language versions, teacher/student versions, etc.

To export notebooks in folder ``L1_python_intro``, call
```
python export_notebooks.py -s L1_python_intro
```

The call will generate different versions under folder ``DRIVE_MATERIAL``. By default, the following versions are generated:
* STUDENTS_SK: The student version of the notebooks in Slovak;
* STUDENTS_EN: The student version of the notebooks in English;
* TEACHERS_EN: The teacher's version of the notebooks in English.

### Prevent a Notebook from Being Exported

If there is any notebook that you are using for testing and you do not want it exported, prepend an underscore ``_`` to its filename. Filenames starting with an underscore are ignored by the export script.

### Cell Tagging

Cell tagging is used to maintain content for the different notebook versions inside a single development notebook. To view and edit tags in Jupyter, select ``View->Cell Toolbar->Tags``.

### Language Versions

Both language versions are maintained inside a single development notebook. The same content is written alternatingly in one and the other language. Keeping different language versions of the same content close to each other makes it much easier to keep them in sync when updating them.

To define the language version of a cell, we use cell tagging. Cells can be tagged with:
* **en**: the cell only goes into the English version;
* **sk**: the cell only goes into the Slovak version;

Cells that are not tagged as either go into both versions.

### The Student and Teacher Versions

Most notebooks include some tasks for students. All development notebooks should include correct answers to these, which, of course, must not be part of the student version of the notebooks. To this end, the export script support two more tags:
* **teacher**: the cell only goes into the teacher version;
* **student**: the cell only goes into the student version;

A further difference between the student and the teacher version is that by default the student version has cell outputs cleared by the export script. The teacher version keeps the outputs, which makes it easier to check whether students' notebooks are giving correct answers.

If there are some cells for which you want to keep the output even in the student version, you can mark them with the **keep** tag.

### Other Tags

If there are some cells in the development version of your notebook that you use for testing, generating figures, etc. – and you do not want them in the exported notebook, you can mark them with the **drop** tag. That way the entire cell (both code and output) will be dropped from all of the exported versions.