import py, os
from pytest import raises
from .support import setup_make, pylong

currpath = py.path.local(__file__).dirpath()
test_dct = str(currpath.join("templatesDict"))

def setup_module(mod):
    setup_make("templates")


class TestTEMPLATES:
    def setup_class(cls):
        cls.test_dct = test_dct
        import cppyy
        cls.templates = cppyy.load_reflection_info(cls.test_dct)

    def test01_template_member_functions(self):
        """Template member functions lookup and calls"""

        import cppyy
        import sys

        m = cppyy.gbl.MyTemplatedMethodClass()

      # implicit (called before other tests to check caching)
        assert m.get_size(1)          == m.get_int_size()+1
        assert 'get_size<int>' in dir(cppyy.gbl.MyTemplatedMethodClass)

      # pre-instantiated
        assert m.get_size['char']()   == m.get_char_size()
        assert m.get_size[int]()      == m.get_int_size()

      # specialized
        if sys.hexversion >= 0x3000000:
            targ = 'long'
        else:
            targ = long
        assert m.get_size[targ]()     == m.get_long_size()

        import ctypes
        assert m.get_size(ctypes.c_double(3.14)) == m.get_size['double']()
        assert m.get_size(ctypes.c_double(3.14).value) == m.get_size['double']()+1

      # auto-instantiation
        assert m.get_size[float]()    == m.get_float_size()
        assert m.get_size['double']() == m.get_double_size()
        assert m.get_size['MyTemplatedMethodClass']() == m.get_self_size()
        assert 'get_size<MyTemplatedMethodClass>' in dir(cppyy.gbl.MyTemplatedMethodClass)

      # auto through typedef
        assert m.get_size['MyTMCTypedef_t']() == m.get_self_size()
        assert 'get_size<MyTMCTypedef_t>' in dir(cppyy.gbl.MyTemplatedMethodClass)
        assert m.get_size['MyTemplatedMethodClass']() == m.get_self_size()

    def test02_non_type_template_args(self):
        """Use of non-types as template arguments"""

        import cppyy

        cppyy.cppdef("template<int i> int nt_templ_args() { return i; };")

        assert cppyy.gbl.nt_templ_args[1]()   == 1
        assert cppyy.gbl.nt_templ_args[256]() == 256

    def test03_templated_function(self):
        """Templated global and static functions lookup and calls"""

        import cppyy

        # TODO: the following only works if something else has already
        # loaded the headers associated with this template
        ggs = cppyy.gbl.global_get_size
        assert ggs['char']() == 1

        gsf = cppyy.gbl.global_some_foo

        assert gsf[int](3) == 42
        assert gsf(3)      == 42
        assert gsf(3.)     == 42

        gsb = cppyy.gbl.global_some_bar

        assert gsb(3)            == 13
        assert gsb['double'](3.) == 13

        # TODO: the following only works in a namespace
        nsgsb = cppyy.gbl.SomeNS.some_bar

        assert nsgsb[3]
        assert nsgsb[3]() == 3

        # TODO: add some static template method

        # test forced creation of subsequent overloads
        from cppyy.gbl.std import vector
        # float in, float out
        ggsr = cppyy.gbl.global_get_some_result['std::vector<float>']
        assert type(ggsr(vector['float']([0.5])).m_retval) == float
        assert ggsr(vector['float']([0.5])).m_retval == 0.5
        # int in, float out
        ggsr = cppyy.gbl.global_get_some_result['std::vector<int>']
        assert type(ggsr(vector['int']([5])).m_retval) == float
        assert ggsr(vector['int']([5])).m_retval == 5.
        # float in, int out
        ggsr = cppyy.gbl.global_get_some_result['std::vector<float>, int']
        assert type(ggsr(vector['float']([0.3])).m_retval) == int
        assert ggsr(vector['float']([0.3])).m_retval == 0
        # int in, int out
        ggsr = cppyy.gbl.global_get_some_result['std::vector<int>, int']
        assert type(ggsr(vector['int']([5])).m_retval) == int
        assert ggsr(vector['int']([5])).m_retval == 5

    def test04_variadic_function(self):
        """Call a variadic function"""

        import cppyy
        std = cppyy.gbl.std

        s = std.ostringstream('(', std.ios_base.ate)
        # Fails; wrong overload on PyPy, none on CPython
        #s << "("
        cppyy.gbl.SomeNS.tuplify(s, 1, 4., "aap")
        assert s.str() == "(1, 4, aap, NULL)"

        cppyy.cppdef("""
            template<typename... myTypes>
            int test04_variadic_func() { return sizeof...(myTypes); }
        """)

        assert cppyy.gbl.test04_variadic_func['int', 'double', 'void*']() == 3

    def test05_variadic_overload(self):
        """Call an overloaded variadic function"""

        import cppyy

        assert cppyy.gbl.isSomeInt(3.)         == False
        assert cppyy.gbl.isSomeInt(1)          == True
        assert cppyy.gbl.isSomeInt()           == False
        assert cppyy.gbl.isSomeInt(1, 2, 3)    == False

    def test06_variadic_sfinae(self):
        """Attribute testing through SFINAE"""

        import cppyy
        cppyy.gbl.AttrTesting      # load
        from cppyy.gbl.AttrTesting import Obj1, Obj2, has_var1, call_has_var1
        from cppyy.gbl.std import move

        assert has_var1(Obj1()) == hasattr(Obj1(), 'var1')
        assert has_var1(Obj2()) == hasattr(Obj2(), 'var1')
        assert has_var1(3)      == hasattr(3,      'var1')
        assert has_var1("aap")  == hasattr("aap",  'var1')

        assert call_has_var1(move(Obj1())) == True
        assert call_has_var1(move(Obj2())) == False

    def test07_type_deduction(self):
        """Traits/type deduction"""

        import cppyy
        cppyy.gbl.AttrTesting      # load
        from cppyy.gbl.AttrTesting import select_template_arg, Obj1, Obj2

       #assert select_template_arg[0, Obj1, Obj2].argument == Obj1
        assert select_template_arg[1, Obj1, Obj2].argument == Obj2
        # TODO: the following only results in a Cling compilation error
        #raises(TypeError, select_template_arg.__getitem__, 2, Obj1, Obj2)

        # TODO, this doesn't work for builtin types as the 'argument'
        # typedef will not resolve to a class
       #assert select_template_arg[1, int, float].argument == float

    def test08_using_of_static_data(self):
        """Derived class using static data of base"""

        import cppyy

      # TODO: the following should live in templates.h, but currently fails
      # in TClass::GetListOfMethods()
        cppyy.cppdef("""
        template <typename T> struct BaseClassWithStatic {
            static T const ref_value;
        };

        template <typename T>
        T const BaseClassWithStatic<T>::ref_value = 42;

        template <typename T>
        struct DerivedClassUsingStatic : public BaseClassWithStatic<T> {
            using BaseClassWithStatic<T>::ref_value;

            explicit DerivedClassUsingStatic(T x) : BaseClassWithStatic<T>() {
                m_value = x > ref_value ? ref_value : x;
            }

            T m_value;
        };""")

        assert cppyy.gbl.BaseClassWithStatic["size_t"].ref_value == 42

        b1 = cppyy.gbl.DerivedClassUsingStatic["size_t"](  0)
        b2 = cppyy.gbl.DerivedClassUsingStatic["size_t"](100)

      # assert b1.ref_value == 42
        assert b1.m_value   ==  0

      # assert b2.ref_value == 42
        assert b2.m_value   == 42

    def test09_templated_callable(self):
        """Test that templated operator() translates to __call__"""

        import cppyy

        tc = cppyy.gbl.TemplatedCallable()

        assert tc(5) == 5.

    def test10_templated_hidding_methods(self):
        """Test that base class methods are not considered when hidden"""

        import cppyy

        B = cppyy.gbl.TemplateHiding.Base
        D = cppyy.gbl.TemplateHiding.Derived

        assert B().callme(1) == 2
        assert D().callme()  == 2
        assert D().callme(2) == 2

    def test11_templated_ctor(self):
        """Test templated constructors"""

        import cppyy

        cppyy.cppdef("""\
        template <typename T>
        class RTTest_SomeClassWithTCtor {
        public:
            template<typename R>
            RTTest_SomeClassWithTCtor(int n, R val) : m_double(n+val) {}
            double m_double;
        };

        namespace RTTest_SomeNamespace {
            template <typename T>
            class RTTest_SomeClassWithTCtor {
            public:
                RTTest_SomeClassWithTCtor() : m_double(-1.) {}
                template<typename R>
                RTTest_SomeClassWithTCtor(int n, R val) : m_double(n+val) {}
                double m_double;
            };
        } """)

        from cppyy import gbl

        assert round(gbl.RTTest_SomeClassWithTCtor[int](1, 3.1).m_double - 4.1, 8) == 0.

        RTTest2 = gbl.RTTest_SomeNamespace.RTTest_SomeClassWithTCtor
        assert round(RTTest2[int](1, 3.1).m_double - 4.1, 8) == 0.
        assert round(RTTest2[int]().m_double + 1., 8) == 0.

    def test12_template_aliases(self):
        """Access to templates made available with 'using'"""

        import cppyy

      # through dictionary
        davec = cppyy.gbl.DA_vector["float"]()
        davec += range(10)
        assert davec[5] == 5

      # through interpreter
        cppyy.cppdef("template<typename T> using IA_vector = std::vector<T>;")
        iavec = cppyy.gbl.IA_vector["float"]()
        iavec += range(10)
        assert iavec[5] == 5

      # with variadic template
        if cppyy.gbl.gInterpreter.ProcessLine("__cplusplus;") > 201402:
            assert cppyy.gbl.using_problem.matryoshka[int, 3].type
            assert cppyy.gbl.using_problem.matryoshka[int, 3, 4].type
            assert cppyy.gbl.using_problem.make_vector[int , 3]
            assert cppyy.gbl.using_problem.make_vector[int , 3]().m_val == 3
            assert cppyy.gbl.using_problem.make_vector[int , 4]().m_val == 4

    def test13_using_templated_method(self):
        """Access to base class templated methods through 'using'"""

        import cppyy

        b = cppyy.gbl.using_problem.Base[int]()
        assert type(b.get3()) == int
        assert b.get3() == 5
        assert type(b.get3['double'](5)) == float
        assert b.get3['double'](5) == 10.

        d = cppyy.gbl.using_problem.Derived[int]()
        #assert type(d.get1['double'](5)) == float
        #assert d.get1['double'](5) == 10.

        assert type(d.get2()) == int
        assert d.get2() == 5

        assert type(d.get3['double'](5)) == float
        assert d.get3['double'](5) == 10.
        assert type(d.get3()) == int
        assert d.get3() == 5

    def test14_templated_return_type(self):
        """Use of a templated return type"""

        import cppyy

        cppyy.cppdef("""\
        struct RTTest_SomeStruct1 {};
        template<class ...T> struct RTTest_TemplatedList {};
        template<class ...T> auto rttest_make_tlist(T ... args) {
            return RTTest_TemplatedList<T...>{};
        }

        namespace RTTest_SomeNamespace {
            struct RTTest_SomeStruct2 {};
            template<class ...T> struct RTTest_TemplatedList2 {};
        }

        template<class ...T> auto rttest_make_tlist2(T ... args) {
            return RTTest_SomeNamespace::RTTest_TemplatedList2<T...>{};
        } """)

        from cppyy.gbl import rttest_make_tlist, rttest_make_tlist2, \
            RTTest_SomeNamespace, RTTest_SomeStruct1

        assert rttest_make_tlist(RTTest_SomeStruct1())
        assert rttest_make_tlist(RTTest_SomeNamespace.RTTest_SomeStruct2())
        assert rttest_make_tlist2(RTTest_SomeStruct1())
        assert rttest_make_tlist2(RTTest_SomeNamespace.RTTest_SomeStruct2())

    def test15_rvalue_templates(self):
        """Use of a template with r-values; should accept builtin types"""

        import cppyy

        is_valid = cppyy.gbl.T_WithRValue.is_valid

      # bit of regression testing
        assert is_valid(3)
        assert is_valid['int'](3)      # used to crash

      # actual method calls
        assert is_valid[int](1)
        assert not is_valid(0)
        assert is_valid(1.)
        assert not is_valid(0.)

    def test16_variadic(self):
        """Range of variadic templates"""

        import cppyy

        ns = cppyy.gbl.some_variadic

        def get_tn(ns):
          # helper to make all platforms look the same
            tn = ns.gTypeName
            tn = tn.replace(' ', '')
            tn = tn.replace('class', '')
            tn = tn.replace('__cdecl', '')
            tn = tn.replace('__thiscall', '')
            tn = tn.replace('__ptr64', '')
            return tn

      # templated class
        a = ns.A['int', 'double']()
        assert get_tn(ns) == "some_variadic::A<int,double>"

      # static functions
        a.sa(1, 1., 'a')
        assert get_tn(ns).find("some_variadic::A<int,double>::void(int&&,double&&,std::") == 0
        ns.A['char&', 'double*'].sa(1, 1., 'a')
        assert get_tn(ns).find("some_variadic::A<char&,double*>::void(int&&,double&&,std::") == 0
        ns.A['char&', 'double*'].sa_T['int'](1, 1., 'a')
        assert get_tn(ns).find("some_variadic::A<char&,double*>::int(int&&,double&&,std::") == 0

      # member functions
        a.a(1, 1., 'a')
        assert get_tn(ns).find("void(some_variadic::A<int,double>::*)(int&&,double&&,std::") == 0
        a.a_T['int'](1, 1., 'a')
        assert get_tn(ns).find("int(some_variadic::A<int,double>::*)(int&&,double&&,std::") == 0

      # non-templated class
        b = ns.B()
        assert get_tn(ns) == "some_variadic::B"

      # static functions
        b.sb(1, 1., 'a')
        assert get_tn(ns).find("some_variadic::B::void(int&&,double&&,std::") == 0
        ns.B.sb(1, 1., 'a')
        assert get_tn(ns).find("some_variadic::B::void(int&&,double&&,std::") == 0
        ns.B.sb_T['int'](1, 1., 'a')
        assert get_tn(ns).find("some_variadic::B::int(int&&,double&&,std::") == 0

      # member functions
        b.b(1, 1., 'a')
        assert get_tn(ns).find("void(some_variadic::B::*)(int&&,double&&,std::") == 0
        b.b_T['int'](1, 1., 'a')
        assert get_tn(ns).find("int(some_variadic::B::*)(int&&,double&&,std::") == 0

    def test17_empty_body(self):
        """Use of templated function with empty body"""

        import cppyy

        f_T = cppyy.gbl.T_WithEmptyBody.some_empty

        assert cppyy.gbl.T_WithEmptyBody.side_effect == "not set"
        assert f_T[int]() is None
        assert cppyy.gbl.T_WithEmptyBody.side_effect == "side effect"

    def test18_greedy_overloads(self):
        """void*/void** should not pre-empt template instantiations"""

        import cppyy

        ns = cppyy.gbl.T_WithGreedyOverloads

      # check that void* does not mask template instantiations
        g1 = ns.WithGreedy1()
        assert g1.get_size(ns.SomeClass(), True) == -1
        assert g1.get_size(ns.SomeClass()) == cppyy.sizeof(ns.SomeClass)

      # check that void* does not mask template instantiations
        g2 = ns.WithGreedy2()
        assert g2.get_size(ns.SomeClass()) == cppyy.sizeof(ns.SomeClass)
        assert g2.get_size(ns.SomeClass(), True) == -1

      # check that unknown classes do not mask template instantiations
        g3 = ns.WithGreedy3()
        assert g3.get_size(ns.SomeClass()) == cppyy.sizeof(ns.SomeClass)
        assert g3.get_size(cppyy.nullptr, True) == -1

    def test19_templated_operator_add(self):
        """Templated operator+ is ambiguous: either __pos__ or __add__"""

        import cppyy
        import cppyy.gbl as gbl

        cppyy.cppdef("""\
        namespace OperatorAddTest {
        template <class V>
        class CustomVec {
            V fX;
        public:
            CustomVec() : fX(0) {}
            CustomVec(const V & a) : fX(a) { }
            V X()  const { return fX; }
            template <class fV> CustomVec operator + (const fV& v) {
                CustomVec<V> u;
                u.fX = fX + v.fX;
                return u;
            }
        }; }""")

        c = gbl.OperatorAddTest.CustomVec['double'](5.3)
        d = gbl.OperatorAddTest.CustomVec['int'](1)

        q = c + d

        assert round(q.X() - 6.3, 8) == 0.

    def test20_templated_ctor_with_defaults(self):
        """Templated constructor with defaults used to be ignored"""

        import cppyy

        cppyy.cppdef("""\
        namespace TemplatedCtor {
        class C {
        public:
            template <typename Integer, typename std::enable_if_t<std::is_integral_v<Integer>, int> = 0>
            C(Integer) {}
            C(const std::string&) {}
        }; } """)

        assert cppyy.gbl.TemplatedCtor.C(0)

    def test21_type_deduction_with_conversion(self):
        """Template instantiation with [] -> std::vector conversion"""

        import cppyy

        cppyy.cppdef("""\
        namespace l2v {
        struct Base {};
        struct Derived : Base {};

        int test1(const std::vector<Base*>& v) { return (int)v.size(); }

        template <typename T>
        int test2(const std::vector<Derived*>& v) { return (int)v.size(); }

        template <typename T>
        int test2a(std::vector<Derived*> v) { return v.size(); }

        template <typename T>
        int test3(const std::vector<Base*>& v) { return (int)v.size(); }
        }""")

        from cppyy.gbl import l2v

        d1 = l2v.Derived()

        assert l2v.test1([d1])     == 1
        assert l2v.test1([d1, d1]) == 2

        assert l2v.test2[int]([d1])     == 1
        assert l2v.test2[int]([d1, d1]) == 2

        assert l2v.test2a[int]([d1])     == 1
        assert l2v.test2a[int]([d1, d1]) == 2

        assert l2v.test3[int]([d1])     == 1
        assert l2v.test3[int]([d1, d1]) == 2

    def test22_type_deduction_of_proper_integer_size(self):
        """Template type from integer arg should be big enough"""

        import cppyy

        cppyy.cppdef("template <typename T> T PassSomeInt(T t) { return t; }")

        from cppyy.gbl import PassSomeInt

        for val in [1, 100000000000, -2**32, 2**32-1, 2**64-1 -2**63]:
            assert val == PassSomeInt(val)

        for val in [2**64, -2**63-1]:
            raises(OverflowError, PassSomeInt, val)

    def test23_overloaded_setitem(self):
        """Template with overloaded non-templated and templated setitem"""

        import cppyy

        MyVec = cppyy.gbl.TemplateWithSetItem.MyVec

        v = MyVec["float"](2)
        v[0] = 1        # used to throw TypeError

    def test24_stdfunction_templated_arguments(self):
        """Use of std::function with templated arguments"""

        import cppyy

        def callback(x):
            return sum(x)

        cppyy.cppdef("""double callback_vector(
            const std::function<double(std::vector<double>)>& callback, std::vector<double> x) {
                return callback(x);
        }""")

        assert cppyy.gbl.std.function['double(std::vector<double>)']

        assert cppyy.gbl.callback_vector(callback, [1, 2, 3]) == 6

        cppyy.cppdef("""double wrap_callback_vector(
             double (*callback)(std::vector<double>), std::vector<double> x) {
                 return callback_vector(callback, x);
        }""")

        assert cppyy.gbl.wrap_callback_vector(callback, [4, 5, 6]) == 15

        assert cppyy.gbl.std.function['double(std::vector<double>)']

    def test25_stdfunction_ref_and_ptr_args(self):
        """Use of std::function with reference or pointer args"""

      # used to fail b/c type trimming threw away end ')' together with '*' or '&'

        import cppyy

        cppyy.cppdef("""\
        namespace LambdaAndTemplates {
        template <typename T>
        struct S {};

        template <typename T>
        bool f(const std::function<bool(const S<T>&)>& callback) {
            return callback({});
        }

        template <typename T>
        bool f_noref(const std::function<bool(const S<T>)>& callback) {
            return callback({});
        }

        struct S0 {};

        bool f_notemplate(const std::function<bool(const S0&)>& callback) {
            return callback({});
        } }""")

        ns = cppyy.gbl.LambdaAndTemplates

        assert ns.f_noref[int](lambda arg: True)
        assert ns.f_notemplate(lambda arg: True)

      # similar/same problem as above
        cppyy.cppdef("""\
        namespace LambdaAndTemplates {
        template <typename T>
        bool f_nofun(bool (*callback)(const S<T>&)) {
            return callback({});
        } }""")

        assert ns.f_nofun[int](lambda arg: True)

      # following used to fail argument conversion
        assert ns.f[int](lambda arg: True)

        cppyy.cppdef("""\
        namespace FuncPtrArrays {
        typedef struct {
            double* a0, *a1, *a2, *a3;
        } Arrays;

        typedef struct {
            void (*fnc) (Arrays* const, Arrays* const);
        } Foo;

        void bar(Arrays* const, Arrays* const) {
            return;
        } }""")

        ns = cppyy.gbl.FuncPtrArrays

        foo = ns.Foo()
        foo.fnc = ns.bar
        foo.fnc       # <- this access used to fail

    def test26_partial_templates(self):
        """Deduction of types with partial templates"""

        import cppyy

        cppyy.cppdef("""\
        template <typename A, typename B>
        B partial_template_foo1(B b) { return b; }

        template <typename A, typename B>
        B partial_template_foo2(B b) { return b; }

        namespace partial_template {
            template <typename A, typename B>
            B foo1(B b) { return b; }

            template <typename A, typename B>
            B foo2(B b) { return b; }
        } """)

        ns = cppyy.gbl.partial_template

        assert cppyy.gbl.partial_template_foo1['double', 'int'](17) == 17
        assert cppyy.gbl.partial_template_foo1['double'](17) == 17

        assert cppyy.gbl.partial_template_foo1['double'](17) == 17
        assert cppyy.gbl.partial_template_foo1['double', 'int'](17) == 17

        assert ns.foo1['double', 'int'](17) == 17
        assert ns.foo1['double'](17) == 17

        assert ns.foo2['double'](17) == 17
        assert ns.foo2['double', 'int'](17) == 17

        cppyy.cppdef("""\
        template <typename A, typename... Other, typename B>
        B partial_template_bar1(B b) { return b; }

        template <typename A, typename... Other, typename B>
        B partial_template_bar2(B b) { return b; }

        namespace partial_template {
            template <typename A, typename... Other, typename B>
            B bar1(B b) { return b; }

            template <typename A, typename... Other, typename B>
            B bar2(B b) { return b; }
        }""")

        assert cppyy.gbl.partial_template_bar1['double','int'](17) == 17
        assert cppyy.gbl.partial_template_bar1['double'](17) == 17

        assert cppyy.gbl.partial_template_bar2['double'](17) == 17
        assert cppyy.gbl.partial_template_bar2['double','int'](17) == 17

        assert ns.bar1['double','int'](17) == 17
        assert ns.bar1['double'](17) == 17

        assert ns.bar2['double'](17) == 17
        assert ns.bar2['double','int'](17) == 17

    def test27_variadic_constructor(self):
        """Use of variadic template function as contructor"""

        import cppyy

        cppyy.cppdef("""\
        namespace VadiadicConstructor {
        class Atom {
        public:
            using mass_type = double;

            Atom() {}

            template<typename... Args>
            explicit Atom(const mass_type& mass_in, Args&&... args) :
              Atom(std::forward<Args>(args)...) {
                constexpr bool is_mass =
                  std::disjunction_v<std::is_same<std::decay_t<Args>, mass_type>...>;
                static_assert(!is_mass, "Please only provide one mass");
                mass() = mass_in;
            }

            mass_type& mass() noexcept {
                return m_m;
            }

            mass_type m_m = 0.0;
        }; }""")

        ns = cppyy.gbl.VadiadicConstructor

        a = ns.Atom(1567.0)
        assert a.m_m == 1567.0

    def test28_enum_in_constructor(self):
        """Use of enums in template function as constructor"""

        import cppyy

        cppyy.cppdef("""\
        namespace EnumConstructor {
        struct ST {
            enum TI { I32 };
        };

        struct FS {
            enum R { EQ, NE, GT, GE, LT, LE };

            template<typename T>
            FS(const std::string&, const ST::TI, R, const T&e) {}
        }; }""")

        ns = cppyy.gbl.EnumConstructor

        assert ns.FS('i', ns.ST.I32,    ns.FS.EQ,   10)
        assert ns.FS('i', ns.ST.TI.I32, ns.FS.R.EQ, 10)


class TestTEMPLATED_TYPEDEFS:
    def setup_class(cls):
        cls.test_dct = test_dct
        import cppyy
        cls.templates = cppyy.load_reflection_info(cls.test_dct)

    def test01_using(self):
        """Test presence and validity of using typededs"""

        import cppyy

        tct = cppyy.gbl.TemplatedTypedefs.DerivedWithUsing
        dum = cppyy.gbl.TemplatedTypedefs.SomeDummy

        assert tct[int, dum, 4].vsize == 4
        assert tct[int, dum, 8].vsize == 8

        in_type = tct[int, dum, 4].in_type
        assert 'in_type' in dir(tct[int, dum, 4])

        assert in_type.__name__ == 'in_type'
        assert in_type.__cpp_name__ == 'TemplatedTypedefs::DerivedWithUsing<int,TemplatedTypedefs::SomeDummy,4>::in_type'

        in_type_tt = tct[int, dum, 4].in_type_tt
        assert 'in_type_tt' in dir(tct[int, dum, 4])

        assert in_type_tt.__name__ == 'in_type_tt'
        assert in_type_tt.__cpp_name__ == 'TemplatedTypedefs::DerivedWithUsing<int,TemplatedTypedefs::SomeDummy,4>::in_type_tt'

    def test02_mapped_type_as_internal(self):
        """Test that mapped types can be used as builting"""

        import cppyy

        tct = cppyy.gbl.TemplatedTypedefs.DerivedWithUsing
        dum = cppyy.gbl.TemplatedTypedefs.SomeDummy

        for argname in ['short', 'unsigned short', 'int']:
            in_type = tct[argname, dum, 4].in_type
            assert issubclass(in_type, int)
            assert in_type(13) == 13
            assert 2*in_type(42) - 84 == 0

        for argname in ['unsigned int', 'long', 'unsigned long']:# TODO: 'long long', 'unsigned long long'
            in_type = tct[argname, dum, 4].in_type
            assert issubclass(in_type, pylong)
            assert in_type(13) == 13
            assert 2*in_type(42) - 84 == 0

        for argname in ['float', 'double', 'long double']:
            in_type = tct[argname, dum, 4].in_type
            assert issubclass(in_type, float)
            assert in_type(13) == 13.
            assert 2*in_type(42) - 84. == 0.

        raises(TypeError, tct.__getitem__, 'gibberish', dum, 4)

    def test03_mapped_type_as_template_arg(self):
        """Test that mapped types can be used as template arguments"""

        import cppyy

        tct = cppyy.gbl.TemplatedTypedefs.DerivedWithUsing
        dum = cppyy.gbl.TemplatedTypedefs.SomeDummy

        in_type = tct['unsigned int', dum, 4].in_type
        assert tct['unsigned int', dum, 4] is tct[in_type, dum, 4]

        in_type = tct['long double', dum, 4].in_type
        assert tct['long double', dum, 4] is tct[in_type, dum, 4]
        assert tct['double', dum, 4] is not tct[in_type, dum, 4]

    def test04_type_deduction(self):
        """Usage of type reducer"""

        import cppyy

        cppyy.cppdef("""
           template <typename T> struct DeductTest_Wrap {
               static auto whatis(T t) { return t; }
           };
        """)

        w = cppyy.gbl.DeductTest_Wrap[int]()
        three = w.whatis(3)
        assert three == 3

    def test05_type_deduction_and_extern(self):
        """Usage of type reducer with extern template"""

        import cppyy
        import sys

        cppyy.cppdef("""\
        namespace FailedTypeDeducer {
        template<class T>
        class A {
        public:
            T result() { return T{5}; }
        };

        extern template class A<int>;
        }""")

        if sys.platform != 'darwin':   # feature disabled
            assert cppyy.gbl.FailedTypeDeducer.A[int]().result()  == 42
        assert cppyy.gbl.FailedTypeDeducer.A['double']().result() == 5.

      # FailedTypeDeducer::B is defined in the templates.h header
        assert cppyy.gbl.FailedTypeDeducer.B['double']().result() == 5.
        assert cppyy.gbl.FailedTypeDeducer.B[int]().result()      == 5


class TestTEMPLATE_TYPE_REDUCTION:
    def setup_class(cls):
        cls.test_dct = test_dct
        import cppyy
        cls.templates = cppyy.load_reflection_info(cls.test_dct)

    def test01_reduce_binary(self):
        """Squash template expressions for binary operations (like in gmpxx)"""

        import cppyy

        e1 = cppyy.gbl.TypeReduction.Expr[int]()
        e2 = cppyy.gbl.TypeReduction.Expr[int]()

        cppyy.py.add_type_reducer('TypeReduction::BinaryExpr<int>', 'TypeReduction::Expr<int>')

        assert type(e1+e2) == cppyy.gbl.TypeReduction.Expr[int]
