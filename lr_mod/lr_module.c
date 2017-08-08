#include <Python.h>

#include <lireader.h>
#include <linumber.h>
#include <liparse.h>
#include <liutility.h>

li_reader *reader;

static PyObject *
lr_put_data(PyObject *self, PyObject *args)
{
    char *data;
    int len, result;

    if (!PyArg_ParseTuple(args, "s#", &data, &len))
        return NULL;

    result = li_put(reader, data, len);

    return Py_BuildValue("i", result);
}

static PyObject *
lr_get_data(PyObject *self, PyObject *args)
{
    int result, count;
    uint64_t bytes = 0;
    double *d;

    if (!PyArg_ParseTuple(args, ""))
        return NULL;

    li_array(double) doubles;
    li_array_ctor(double)(&doubles);

    result = li_get(reader, LI_RECORD_BYTES_U64, 0, &bytes, sizeof(bytes));

    if (!bytes)
        return Py_BuildValue("()");

    count = bytes / sizeof(double);

    li_array_resize(double)(&doubles, (size_t) bytes / sizeof(double), 0.0);

    result = li_get(reader, LI_RECORD_F64V, 0, li_array_begin(double)(&doubles), li_array_size(double)(&doubles) * sizeof(double));

    if (result != LI_SUCCESS)
        return Py_BuildValue("()");
    
    // FIXME: Macros or direct manipulation using PyList_*
    d = doubles.begin;
    switch(count){
        case 1:    return Py_BuildValue("(d)", d[0]);
        case 2:    return Py_BuildValue("(d,d)", d[0], d[1]);
        case 3:    return Py_BuildValue("(d,d,d)", d[0], d[1], d[2]);
        case 4:    return Py_BuildValue("(d,d,d,d)", d[0], d[1], d[2], d[3]);
        case 5:    return Py_BuildValue("(d,d,d,d,d)", d[0], d[1], d[2], d[3], d[4]);
        case 6:    return Py_BuildValue("(d,d,d,d,d,d)", d[0], d[1], d[2], d[3], d[4], d[5]);
        default:   return Py_BuildValue("()");
    }
}

static PyObject * lr_restart(PyObject *self, PyObject *args)
{
    if (reader)
        li_finalize(reader);
    
    reader = li_init(malloc, free);

    Py_RETURN_NONE;
}

static PyMethodDef LrMethods[] = {
    {"put", lr_put_data, METH_VARARGS, "Put raw data in"},
    {"get", lr_get_data, METH_VARARGS, "Get records out"},
    {"restart", lr_restart, METH_VARARGS, "(re)-initialise internal state"},
    {NULL, NULL, 0, NULL}
};

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef LrModule = {
   PyModuleDef_HEAD_INIT,
   "lr",
   NULL,
   -1,
   LrMethods
};

PyMODINIT_FUNC PyInit_lr(void)
{
    return PyModule_Create(&LrModule);
}

#else // Py3K

PyMODINIT_FUNC initlr(void)
{
    return Py_InitModule("lr", LrMethods);
}

#endif
