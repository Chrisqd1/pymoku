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
    uint8_t chs;
    double *d;

    if (!PyArg_ParseTuple(args, ""))
        return NULL;

    li_array(double) doubles;
    li_array_ctor(double)(&doubles);

    result = li_get(reader, LI_RECORD_BYTES_U64, 0, &bytes, sizeof(bytes));

    if (result != LI_SUCCESS) {
        PyErr_Format(PyExc_Exception, "LiquidReader doesn't have header, error %d", result);
        return NULL;
    }

    if (!bytes)
        Py_RETURN_NONE;

    count = bytes / sizeof(double);

    li_array_resize(double)(&doubles, (size_t) bytes / sizeof(double), 0.0);

    // This always succeeds if the above record length one did (the whole header is parsed at once)
    li_get(reader, LI_CHANNEL_SELECT_U8, 0, &chs, sizeof(chs));

    result = li_get(reader, LI_RECORD_F64V, 0, li_array_begin(double)(&doubles), li_array_size(double)(&doubles) * sizeof(double));

    if (result == LI_SMALL_SRC) {
        Py_RETURN_NONE;
    } else if (result != LI_SUCCESS) {
        PyErr_Format(PyExc_Exception, "LiquidReader error %d", result);
        return NULL;
    }

    // FIXME: Macros or direct manipulation using PyList_*
    d = doubles.begin;

    if (chs == 1 || chs == 2) {
        switch(count){
            case 0:    Py_RETURN_NONE;
            case 1:    return Py_BuildValue("d", d[0]);
            case 2:    return Py_BuildValue("(dd)", d[0], d[1]);
            case 3:    return Py_BuildValue("(ddd)", d[0], d[1], d[2]);
            case 4:    return Py_BuildValue("(dddd)", d[0], d[1], d[2], d[3]);
            case 5:    return Py_BuildValue("(ddddd)", d[0], d[1], d[2], d[3], d[4]);
            case 6:    return Py_BuildValue("(dddddd)", d[0], d[1], d[2], d[3], d[4], d[5]);
            case 7:    return Py_BuildValue("(ddddddd)", d[0], d[1], d[2], d[3], d[4], d[5], d[6]);
            default:   PyErr_Format(PyExc_Exception, "Unknown record count %d for ch %d", count, chs); return NULL;
        }
    } else { // Both channels active, need to split the record in half
        switch(count){
            case 0:    Py_RETURN_NONE;
            case 2:    return Py_BuildValue("(dd)", d[0], d[1]);
            case 4:    return Py_BuildValue("((dd)(dd))", d[0], d[1], d[2], d[3]);
            case 6:    return Py_BuildValue("((ddd)(ddd)", d[0], d[1], d[2], d[3], d[4], d[5]);
            case 8:    return Py_BuildValue("((dddd)(dddd))", d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7]);
            case 10:   return Py_BuildValue("((ddddd)(ddddd))", d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9]);
            case 12:   return Py_BuildValue("((dddddd)(dddddd))", d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], d[10], d[11]);
            case 14:   return Py_BuildValue("((dddddd)(dddddd))", d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], d[10], d[11], d[12], d[13]);
            default:   PyErr_Format(PyExc_Exception, "Unknown record count %d for ch %d", count, chs); return NULL;
        }
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
    Py_InitModule("lr", LrMethods);
}

#endif
