import tensorflow as tf
import numpy as np
from scipy import interpolate



def gen_source(x_src = 0, y_src = 0, sigma_src = 1, numpix_side = 192):
    
    x = np.linspace(-1, 1, numkappa_side) * kap_side_length/2
    y = np.linspace(-1, 1, numkappa_side) * kap_side_length/2
    Xsrc, Ysrc = np.meshgrid(x, y)
    
    Im = np.sqrt(((Xsrc-x_src)**2+(Ysrc-y_src)**2) / (2.*sigma_src**2) )
    
    return Im



def Kappa_fun(xlens, ylens, elp, phi, sigma_v, numkappa_side = 193, kap_side_length = 2, rc=0, Ds = 1753486987.8422, Dds = 1125770220.58881, c = 299800000):
    
    x = np.linspace(-1, 1, numkappa_side) * kap_side_length/2
    y = np.linspace(-1, 1, numkappa_side) * kap_side_length/2
    xv, yv = np.meshgrid(x, y)
    
    A = (y[1]-y[0])/2. *(2*np.pi/ (360*3600) )
    
    rcord, thetacord = np.sqrt(xv**2 + yv**2) , np.arctan2(xv, yv)
    thetacord = thetacord - phi
    Xkap, Ykap = rcord*np.cos(thetacord), rcord*np.sin(thetacord)
    
    rlens, thetalens = np.sqrt(xlens**2 + ylens**2) , np.arctan2(xlens, ylens)
    thetalens = thetalens - phi
    xlens, ylens = rlens*np.cos(thetalens), rlens*np.sin(thetalens)
    
    r = np.sqrt((Xkap-xlens)**2 + ((Ykap-ylens) * (1-elp) )**2) *(2*np.pi/ (360*3600) )
    
    Rein = (4*np.pi*sigma_v**2/c**2) * Dds /Ds 
    
    kappa = np.divide( np.sqrt(1-elp)* Rein ,  (2* np.sqrt( r**2 + rc**2)))
    
    mass_inside_00_pix = 2.*A*(np.log(2.**(1./2.) + 1.) - np.log(2.**(1./2.)*A - A) + np.log(3.*A + 2.*2.**(1./2.)*A))
    
    print A
    print mass_inside_00_pix
    
    density_00_pix = np.sqrt(1.-elp) * Rein/(2.) * mass_inside_00_pix/((2.*A)**2.)
    
    print density_00_pix
    
    ind = np.argmin(r)
    
    kappa.flat[ind] = density_00_pix
    
    return kappa

    
class Likelihood(object):
    '''
    This class will contain the
    likelihood that will be fed to the RIM

    '''
    #img_pl,lens_pl,noise,noise_cov
    def __init__(self, im_side= 2., src_res=0.016, numpix_side = 192):
        '''
        Initialize the object.
        '''
        
        self.im_side = im_side 
        self.numpix_side = numpix_side
        self.src_res     = src_res


    def get_deflection_angles(self, Xim, Yim, Kappa, kap_cent, kap_side):
        #Calculate the Xsrc, Ysrc from the Xim, Yim for a given kappa map
        
        kap_numpix = (Kappa.shape.as_list())[1]
        dx_kap = kap_side/(kap_numpix-1)
        
        x = tf.linspace(-1., 1., kap_numpix*2)*kap_side
        y = tf.linspace(-1., 1., kap_numpix*2)*kap_side
        X_filt, Y_filt = tf.meshgrid(x, y)
        
        kernel_denom = tf.square(X_filt) + tf.square(Y_filt)
        Xconv_kernel = tf.divide(X_filt , kernel_denom) 
        Yconv_kernel = tf.divide(Y_filt , kernel_denom) 
        
        Xconv_kernel = tf.reshape(Xconv_kernel, [kap_numpix*2, kap_numpix*2, 1,1])
        Yconv_kernel = tf.reshape(Yconv_kernel, [kap_numpix*2, kap_numpix*2, 1,1])
        
        alpha_x = tf.nn.conv2d(Kappa, Xconv_kernel, [1, 1, 1, 1], "SAME") * (dx_kap**2/np.pi);
        alpha_y = tf.nn.conv2d(Kappa, Yconv_kernel, [1, 1, 1, 1], "SAME") * (dx_kap**2/np.pi);
        
        
        #X_kap = tf.linspace(-0.5, 0.5, kap_numpix)*kap_side/1.
        #Y_kap = tf.linspace(-0.5, 0.5, kap_numpix)*kap_side/1.
        #Xkap, Ykap = tf.meshgrid(X_kap, Y_kap)
        
        Xim = tf.reshape(Xim, [-1, self.numpix_side, self.numpix_side, 1])
        Yim = tf.reshape(Yim, [-1, self.numpix_side, self.numpix_side, 1])
        
        
        x_centshif = -(kap_cent[0]*(1./dx_kap))*tf.ones([1, self.numpix_side, self.numpix_side, 1], dtype=tf.float32) 
        x_centshif = tf.reshape(x_centshif, [-1, self.numpix_side, self.numpix_side, 1])
        x_resize = tf.scalar_mul( (1./dx_kap), tf.math.add(Xim, 0.5*kap_side*tf.ones([1, self.numpix_side, self.numpix_side, 1], dtype=tf.float32)) )
        x_resize = tf.reshape(x_resize, [-1, self.numpix_side, self.numpix_side, 1])
        
        Xim_pix = tf.math.add( x_centshif , x_resize )  
        
        
        
        y_centshif = -(kap_cent[1]*(1./dx_kap))*tf.ones([1, self.numpix_side, self.numpix_side, 1], dtype=tf.float32) 
        y_centshif = tf.reshape(y_centshif, [-1, self.numpix_side, self.numpix_side, 1])
        y_resize = tf.scalar_mul( (1./dx_kap), tf.math.add(Yim, 0.5*kap_side*tf.ones([1, self.numpix_side, self.numpix_side, 1], dtype=tf.float32)) )
        y_resize = tf.reshape(y_resize, [-1, self.numpix_side, self.numpix_side, 1])
        
        Yim_pix = tf.math.add( y_centshif , y_resize )  
        
        
        
        Xim_pix = tf.reshape(Xim_pix ,  [1, self.numpix_side, self.numpix_side, 1])
        Yim_pix = tf.reshape(Yim_pix ,  [1, self.numpix_side, self.numpix_side, 1])
        
        wrap = tf.reshape( tf.stack([Xim_pix, Yim_pix], axis = 3), [1, self.numpix_side, self.numpix_side, 2])
        
        
        X_im_interp = tf.contrib.resampler.resampler(alpha_x, wrap)
        Y_im_interp = tf.contrib.resampler.resampler(alpha_y, wrap)
        
        Xsrc = tf.math.add(tf.reshape(Xim, [1, self.numpix_side, self.numpix_side, 1]),  alpha_x )
        Ysrc = tf.math.add(tf.reshape(Yim, [1, self.numpix_side, self.numpix_side, 1]),  alpha_y )
        
        return Xsrc, Ysrc
    
    def get_lensed_image(self, Kappa, kap_cent, kap_side, Src):
        
        x = tf.linspace(-1., 1., self.numpix_side)*self.im_side/2.
        y = tf.linspace(-1., 1., self.numpix_side)*self.im_side/2.
        Xim, Yim = tf.meshgrid(x, y)
        
        
        Xsrc, Ysrc = self.get_deflection_angles(Xim, Yim, Kappa, kap_cent, kap_side)
        
        Xsrc = tf.reshape(Xsrc, [-1, self.numpix_side, self.numpix_side, 1])
        Ysrc = tf.reshape(Ysrc, [-1, self.numpix_side, self.numpix_side, 1])
        
        #self.src_side = self.src_res *(self.numpix_side-1)
        
        #dx = self.src_side/(self.numpix_side-1)
        
        
        #Xsrc_pix = tf.scalar_mul( (1./dx), tf.math.add(Xsrc, self.src_side/2.*tf.ones([1, self.numpix_side, self.numpix_side, 1], dtype=tf.float32)) )
        #Ysrc_pix = tf.scalar_mul( (1./dx), tf.math.add(Ysrc, self.src_side/2.*tf.ones([1, self.numpix_side, self.numpix_side, 1], dtype=tf.float32)) )
        
        Xsrc_pix, Ysrc_pix = self.coord_to_pix(Xsrc,Ysrc,0.,0.,self.src_res *(self.numpix_side-1),self.numpix_side)
        
        wrap = tf.reshape( tf.stack([Xsrc_pix, Ysrc_pix], axis = 3), [1, self.numpix_side, self.numpix_side, 2])
        
        
        IM = tf.contrib.resampler.resampler(Src, wrap)
        
        return IM, Xsrc_pix, Ysrc_pix
    


    def coord_to_pix(self,X,Y,Xc,Yc,l,N):
    
        xmin = Xc-0.5*l
        ymin = Yc-0.5*l
        dx = l/(N-1.)

        j = tf.scalar_mul(1./dx, tf.math.add(X, -1.* xmin))
        i = tf.scalar_mul(1./dx, tf.math.add(Y, -1.* ymin))
        
        return j, i
        
        