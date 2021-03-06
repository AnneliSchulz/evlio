// -*- mode: c++; c-basic-offset: 4 -*-
#ifndef _FITSRECORD_H_
#define _FITSRECORD_H_

#include <map>
#include <vector>
#include <iostream>
#include <iomanip>
#ifndef __MAKECINT__
#include <fitsio.h>
#else
class fitsfile;
#endif
#include <stdexcept>
#include <sstream>
#include <cstring>

#define USE_STREAMER_TO_STRING -999 // for these types, use TSTRING and the c++ streamer

#ifndef __MAKECINT__
// Let the compiler deal with mapping C++ types to FITS DTYPES:
static int getFITSType( double x )		{ return TDOUBLE;	}
static int getFITSType( long double x )		{ return TDOUBLE;	}
static int getFITSType( float x )		{ return TFLOAT;	}
static int getFITSType( int x )		        { return TINT;		}
static int getFITSType( unsigned long x )	{ return TULONG;	}
static int getFITSType( long x )		{ return TLONG;		}
static int getFITSType( long long x )	        { return TLONGLONG;	}
static int getFITSType( bool x )		{ return TBIT;		}
static int getFITSType( char x )		{ return TBYTE;	        }
static int getFITSType( unsigned char x )	{ return TBYTE;	        }
static int getFITSType( unsigned short x )	{ return TUSHORT;	}
static int getFITSType( short x )	        { return TSHORT;	}
static int getFITSType( std::string x )         { return USE_STREAMER_TO_STRING; }
#else
// Let the compiler deal with mapping C++ types to FITS DTYPES:
static int getFITSType( double x );		
static int getFITSType( float x );		
static int getFITSType( int x )	;	        
static int getFITSType( unsigned long x );	
static int getFITSType( long x );		
static int getFITSType( long long x );	        
static int getFITSType( bool x );		
static int getFITSType( char x );		
static int getFITSType( unsigned char x );	
static int getFITSType( unsigned short x );	
static int getFITSType( short x );	        
static int getFITSType( std::string x ) ;        
#endif


/**
 * Exception thrown when problems happen during writing
 */
class FITSRecordError : public std::runtime_error {
public:				       
    FITSRecordError( std::string what ) 
	: std::runtime_error(std::string("(FITSRecord) "+what).c_str()) {;}
};


/**
 * A helper class used only internally by FITSRecord to store
 * information about a column. Subclasses exist for each supported
 * data type to facilitate automatic mapping of columns to
 * data. Data types are automatically handled this way, so the
 * user can't make a mistake.
 *
 * Subclasses must define _valp and _type and implement the stream()
 * method (typically trivially using the streamScalar() helper
 * method).
 *
 * If any additional type conversion (outside of what CFITSIO does
 * automatically) can be implemented by overriding
 * getVoidPointerToValue(), which defaults to simply returning _valp.
 */
class Val {

public:

    Val() 
	: _valp(NULL), _type(TINT), _nelements(1), _is_hex(0) { ; }
    virtual ~Val() {;}

    virtual std::ostream& stream(std::ostream&) = 0;
    virtual void*  getVoidPointerToValue() { return _valp; }
    int    getType() { return _type; }
    virtual int    getSize() { return _nelements; }
    virtual bool isVariableLength() { return false; }

protected:

    void*  _valp;   //!< the stored value as a void* pointer
    int    _type;   //!< the FITS data type
    unsigned long   _nelements;  //!< width of data if array (default 1)
    bool   _is_hex; //!< whether or not to print as hexidecimal

};

/**
 * Template class for storing a scalar value and mapping it to a FITS type
 */ 
template <class Type>
class ScalarVal : public Val {
public:
    ScalarVal( Type &val ) {
	_valp = (void*) &val;
	_type = getFITSType(val);
    }
    virtual std::ostream& stream( std::ostream &stream ) {
	Type val = *((Type*) _valp);
	stream << val;
	return stream;
    }
};

/**
 * Template class for storing a fixed-length array value and mapping
 * it to a FITS type
 */ 
template <class Type>
class ArrayVal : public Val {
public:
    ArrayVal( Type val[], size_t arraysize, unsigned long *sizep=NULL ) {
	_valp = (void*) &val[0];
	_type = getFITSType(val[0]);
	_nelements = (int) arraysize;
	_sizep=sizep;
    }
    virtual std::ostream& stream( std::ostream &stream ) {
	Type *val = ((Type*) _valp);
	stream << "[" << _nelements<<":";
	for (size_t ii=0; ii < _nelements; ii++) {
	    if (_is_hex) stream << "0x"<< std::hex ;
	    stream << val[ii];
	    if (ii != _nelements-1) stream << ",";
	}
	stream << "]";
	return stream;
    }
    virtual int  getSize() { 
	if (_sizep) 
	    return *_sizep;
	else return _nelements; 
    }

    virtual bool isVariableLength() { return _sizep != NULL; }

private:
    unsigned long*  _sizep;  //!< pointer to a size for var-length arrays

};


/**
 * Class to facilitate writing to FITS binary tables that have already
 * been defined (via e.g. a template). 
 *
 * \author Karl Kosack <karl.kosack@cea.fr>
 *
 * The set of methods mapColumnToVar() are defined to make it simple
 * to connect C variables to FITS column types with little chance of
 * making mistakes. Internally, some hidden C++ template and virtual
 * function trickery is used to store the mappings and use them to
 * write the FITS table.
 *
 * Currently supported are single variables of various types (see
 * the set of functions called getFITSType()) a well as
 * fixed-length C-style arrays (e.g. float a[10]).  To add new
 * types, typically one needs only to add a new getFITSType()
 * function.
 *
 * To write a binary FITS table, follow this procedure: 
 * 
 * - constuct a FITSRecord, (either from an open FITS file or
 *    giving the filename and template to use if the file doesn't
 *    exist)
 *
 * - map your local variables to FITS columns using mapColumnToVar()
 *
 * - loop over your data, setting the local variables appropriately,
 *   and calling write() for each data row
 *
 * - when the FITSRecord goes out of scope (or is deleted), the
 *   file is automatically closed and writing finishes.
 * 
 * Example:
 * \code
 *   ... 
 *
 *   FITSRecord rec( "output.fits", "template.tpl", "EVENTS" );
 *   float energy;
 *   unsigned long eventID;
 *   double eventTime;
 *
 *   rec.mapColumnToVar( "ENERGY", energy );    
 *   rec.mapColumnToVar( "EVENTID", eventID );    
 *   rec.mapColumnToVar( "TIME", eventTime );    
 *
 *   for (int ii=0; ii < 50; ii++) {
 *	   energy = 1.1;
 *	   eventID = ii;
 *	   eventTime = ii*0.001; 
 *	   cout << rec << endl;        
 *	   rec.write();
 *    }
 * \endcode
 *
 * a more complete example is shown in  fitsrecordtest.cpp
 *
 * \note rather than constructing a FITSRecord directly, you may just
 * generate a subclass and do all the column mapping in the
 * constructor.  
 *
 * Important Caveats:
 *
 * To use a string variable in a table, use a char[] array and map the
 * column as follows (giving the fixed size of the field, which should
 * match the template).  *
 * \code 
 * char value[30];
 * strcpy( value, "A test" );
 * rec.mapColumnToVar( "MYCOLUMN", value, 30 );
 * \endcode
 * Eventually this should be fixed to work
 * properly with std::strings, but right now it does not.
 *
 */
class FITSRecord {

public:
    
    FITSRecord( fitsfile *fptr);
    FITSRecord( std::string fits_filename, std::string template_filename,
		std::string extension_name="", int extension_version=0 );
    
    ~FITSRecord();




    /**
     * Handle mapping of scalar values to columns (assume values
     * that are not pointers are single values)
     *
     * Example
     * \code
     * double energy = 10.6;
     * mapColumnToVar( "ENERGY", energy );
     * \endcode
     */
    template <class Type> 
    void mapColumnToVar( std::string column, Type &value ) {
	addToMap( column, new ScalarVal<Type>( value ) );
    }

    /**
     * Handle mapping of (fixed-length) arrays to columns. You
     * should specify the size of the array too (otherwise only
     * the first element will be written). 
     *
     * the last option, sizep, can be used to specify a pointer to a
     * size for variable-length arrays.
     *
     * Example
     * \code
     * double arrval[10];
     * mapColumnToVar( "ARRVAL", arrval, 10 );
     * \endcode
     */
    template <class Type> 
    void mapColumnToVar( std::string column, Type value[], int n=1,unsigned long *sizep=NULL ) {
	addToMap( column, new ArrayVal<Type>( value,n,sizep  ) );
    }
    

    void	   write() throw (FITSRecordError);
    std::ostream&  print( std::ostream &stream );
    unsigned long  getNumWritten() { return _rowcount; }
    fitsfile*	getFITSFilePointer() { return _fptr; }
    void	allocateRows( size_t num_rows );
    void        truncateRows( size_t start_row);
    void setVerbose( int level=1 ) { _verbose = level; }
    int  getExtensionVersion() { return _extension_version; }
    bool hasColumn( std::string colname );

    void finishWriting();

    /**
     * write a header keyword to the current HDU. \throws
     * runtime_error if the header isn't already
     * defined. Variables of any type that is mapped by
     * getFITSType(x) can be used.
     *
     * \code
     * rec.writeHeader( "EMAX", 2.0f );  // writes a float
     * rec.writeHeader( "VERSION", 6 );  // writes int
     * \endcode
     */
    template<class Type> 
    void writeHeader( std::string keyword, Type value ) {
	
	Type dummy;
	int fitstype= getFITSType( dummy );
	int status=0;

	// check if keyword is defined:
	char junk[81], comment[81];
	char ckeyword[81];
	strcpy( ckeyword, keyword.c_str() ); 
	fits_read_keyword( _fptr, ckeyword, junk, comment, &status);
	
	if (status)
	    throw FITSRecordError("writeHeader: "+keyword+" "
				  +getFITSError(status));


	if (fitstype == USE_STREAMER_TO_STRING) {
	    // handle this type specially: conver it to a string using
	    // a streamer, and write it as a string
	    if (_verbose >= 2)
		std::cout << "Writing " << keyword
			  << " using streamer -> TSTRING" << std::endl;
	    
	    std::ostringstream str;
	    str << value;
	    // write with the longstr version, in case the string is
	    // larger than 68 characters!
	    char *longstr = new char[str.str().length()+1];
	    strcpy(longstr, str.str().c_str());
 	    fits_update_key_longstr( _fptr, ckeyword, longstr,NULL,&status );
	    delete longstr;

	}
	else {

	    if (_verbose >= 2) 
		std::cout << "Writing " << keyword 
			  << " using type " << fitstype << std::endl;

	    fits_update_key( _fptr, fitstype, ckeyword, (void*)&value, 
			     NULL, &status );
	}


	if (status)
	    throw FITSRecordError("writeHeader: "+keyword+" "
				  +getFITSError(status));

    }
     
    bool printFITSTypes();
  
     
private:

    // helper struct for returning information about a column
    struct ColInfo {
	std::string name;
	int num;
	int typecode;
	long int repeat;
	long int width;
    };

    std::string	 getFITSError( int status );
    void		 addToMap( std::string column, Val *colval );
    ColInfo		 lookupColInfo( std::string column );
    void		 writeDate();
    
    std::map<int,std::string> _namemap;
    std::map<int,Val*> _colmap; //!< maps column number to variable
    fitsfile * _fptr; //!
    bool  _own_fptr;  //!< whether or not we own the fptr or if it was passed in
    unsigned long _rowcount;
    int _verbose;
    int _extension_version;
    

};

std::ostream& operator<<( std::ostream &stream, FITSRecord &rec );
std::ostream& operator<<( std::ostream& stream, Val &colval );



#endif /* _FITSRECORD_H_ */
